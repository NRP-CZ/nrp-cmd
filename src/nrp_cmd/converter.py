import json as _json
import logging
from collections.abc import Callable
from datetime import datetime
from functools import partial
from typing import (
    Any,
    Optional,
    Protocol,
    Self,
    TypeVar,
    cast,
    dataclass_transform,
    get_args,
    get_origin,
)

from attrs import Attribute, define, fields
from cattrs import Converter
from cattrs.dispatch import StructureHook, UnstructureHook
from cattrs.gen import (
    AttributeOverride,
    make_dict_structure_fn,
    make_dict_unstructure_fn,
    override,
)
from yarl import URL

from .errors import StructureError, UnstructureError


def _remove_nulls(data):
    if isinstance(data, dict):
        for key, value in list(data.items()):
            if value is None:
                del data[key]
            else:
                _remove_nulls(value)
    elif isinstance(data, list):
        for idx in range(len(data) - 1, -1, -1):
            if data[idx] is None:
                del data[idx]
        for item in data:
            _remove_nulls(item)


class NullRemovingConverter(Converter):
    def unstructure(
        self, obj: Any, unstructure_as: Any = None, keep_nulls=False
    ) -> Any:
        try:
            ret = super().unstructure(obj, unstructure_as)
            if not keep_nulls:
                _remove_nulls(ret)
            return ret
        except Exception as e:
            raise UnstructureError(str(e)) from e

    def structure(self, obj: Any, type_: type) -> Any:
        try:
            return super().structure(obj, type_)
        except Exception as e:
            raise StructureError(str(e)) from e

converter = NullRemovingConverter()


class TypeHookStructureWrapper(Protocol):
    """Wrapper for structure hooks."""

    def __call__(self, data: Any, type_: type, previous: StructureHook) -> Any:
        """Wrap the structure hook."""
        ...


class TypeHookUnstructureWrapper(Protocol):
    """Wrapper for unstructure hooks."""

    def __call__(self, data: Any, previous: UnstructureHook) -> Any:
        """Wrap the unstructure hook."""
        ...


def structure_extra_data_hook(data: Any, type_: type, previous: StructureHook) -> Any:
    """Structure hook for extra data that moves extra data to a separate _extra_data attribute."""
    ret = previous(data, type)
    keys: set[str] = set()

    fld: Attribute
    for fld in fields(type_):
        if fld.alias:
            keys.add(fld.alias)
        else:
            keys.add(fld.name)
    extra_keys = data.keys() - keys
    extra_data = {k: data[k] for k in extra_keys}
    ret._extra_data = extra_data
    return ret


def unstructure_extra_data_hook(data: Any, previous: UnstructureHook) -> Any:
    """Unstructure hook for extra data that merges extra data from _extra_data attribute."""
    if "_extra_data" not in data.__dict__:
        return previous(data)
    extra_data = data._extra_data
    data = previous(data)
    data.pop("_extra_data", None)
    data.update(extra_data)
    return data


class TypeHookBuilder:
    """Builder for type hooks."""

    def __init__(self, t: type, allow_extra_data: bool) -> None:
        """Initialize the builder."""
        self._type = t
        self._structure_omitted_fields: list[str] = []
        self._unstructure_omitted_fields: list[str] = []
        self._rename_fields: dict[str, str] = {}
        self._structure_wrappers: list[TypeHookStructureWrapper] = []
        self._unstructure_wrappers: list[TypeHookUnstructureWrapper] = []
        self._allow_extra_data = allow_extra_data

    def omit_from_structure(self, *fields: str) -> Self:
        """Omit fields from structuring (deserialization)."""
        self._structure_omitted_fields.extend(fields)
        return self

    def omit_from_unstructure(self, *fields: str) -> Self:
        """Omit fields from unstructuring (serialization)."""
        self._unstructure_omitted_fields.extend(fields)
        return self

    def omit(self, *fields: str) -> Self:
        """Omit fields from both structuring and unstructuring."""
        self.omit_from_structure(*fields)
        self.omit_from_unstructure(*fields)
        return self

    def rename_field(self, serialized_name: str, model_name: str) -> Self:
        """Rename a field."""
        self._rename_fields[serialized_name] = model_name
        return self

    def add_structure_wrapper(self, wrapper: TypeHookStructureWrapper) -> Self:
        """Add a custom function for structuring."""
        self._structure_wrappers.append(wrapper)
        return self

    def add_unstructure_wrapper(self, wrapper: TypeHookUnstructureWrapper) -> Self:
        """Add a custom function for unstructuring."""
        self._unstructure_wrappers.append(wrapper)
        return self

    def build_type_hook(self) -> None:
        """Build and register the type hook."""
        if self._allow_extra_data:
            self._structure_wrappers.append(structure_extra_data_hook)
            self._unstructure_wrappers.append(unstructure_extra_data_hook)

        structure_overrides: dict[str, AttributeOverride] = {}
        for serialized_name, model_name in self._rename_fields.items():
            structure_overrides[model_name] = override(rename=serialized_name)
        for field in self._structure_omitted_fields:
            structure_overrides[field] = override(omit=True)

        unstructure_overrides: dict[str, AttributeOverride] = {}
        for serialized_name, model_name in self._rename_fields.items():
            unstructure_overrides[model_name] = override(rename=serialized_name)
        for field in self._unstructure_omitted_fields:
            unstructure_overrides[field] = override(omit=True)

        st_hook: StructureHook = make_dict_structure_fn(
            self._type, converter, **structure_overrides
        )

        unst_hook: UnstructureHook = make_dict_unstructure_fn(
            self._type, converter, **unstructure_overrides
        )
        if self._structure_wrappers:
            structure_wrappers: list[StructureHook] = []
            for structure_wrapper in self._structure_wrappers:
                if structure_wrappers:
                    structure_wrappers.append(
                        partial(structure_wrapper, previous=structure_wrappers[-1])
                    )
                else:
                    structure_wrappers.append(
                        partial(structure_wrapper, previous=st_hook)
                    )
            st_hook = structure_wrappers[-1]

        if self._unstructure_wrappers:
            unstructure_wrappers: list[UnstructureHook] = []
            for unstructure_wrapper in self._unstructure_wrappers:
                if unstructure_wrappers:
                    unstructure_wrappers.append(
                        partial(unstructure_wrapper, previous=unstructure_wrappers[-1])
                    )
                else:
                    unstructure_wrappers.append(
                        partial(unstructure_wrapper, previous=unst_hook)
                    )
            unst_hook = unstructure_wrappers[-1]

        converter.register_structure_hook(self._type, st_hook)
        converter.register_unstructure_hook(self._type, unst_hook)


class SerializationExtension:
    """Base class for serialization extensions."""

    def apply(self, builder: TypeHookBuilder) -> None:
        """Apply the extension to the builder."""
        pass


@define
class Omit(SerializationExtension):
    """Omit a field from serialization."""

    field: str
    from_structure: bool = True
    from_unstructure: bool = True

    def apply(self, builder: TypeHookBuilder) -> None:
        """Apply the extension to the builder."""
        if self.from_structure:
            builder.omit_from_structure(self.field)
        if self.from_unstructure:
            builder.omit_from_unstructure(self.field)


@define
class Rename(SerializationExtension):
    """Rename a field in serialization."""

    serialized_name: str
    model_name: str

    def apply(self, builder: TypeHookBuilder) -> None:
        """Apply the extension to the builder."""
        builder.rename_field(self.serialized_name, self.model_name)


@define
class WrapStructure(SerializationExtension):
    """Wrap a structure hook."""

    wrapper: TypeHookStructureWrapper

    def apply(self, builder: TypeHookBuilder) -> None:
        """Apply the extension to the builder."""
        builder.add_structure_wrapper(self.wrapper)


@define
class WrapUnstructure(SerializationExtension):
    """Wrap an unstructure hook."""

    wrapper: TypeHookUnstructureWrapper

    def apply(self, builder: TypeHookBuilder) -> None:
        """Apply the extension to the builder."""
        builder.add_unstructure_wrapper(self.wrapper)


C = TypeVar("C", bound=type)


@dataclass_transform()
def extend_serialization(
    *modifications: SerializationExtension,
    allow_extra_data: bool = False,
) -> Callable[[C], C]:
    """Add serialization rules to an attrs class."""

    def wrapper(t: C) -> C:
        """Wrap the class and register type for that."""
        th = TypeHookBuilder(t, allow_extra_data)
        for modification in modifications:
            modification.apply(th)
        th.build_type_hook()
        return t

    return wrapper


def structure_url_hook(value: str, type: type) -> URL:
    """Cattrs converter for URL."""
    return URL(value)


def unstructure_url_hook(value: URL) -> str:
    """Cattrs converter for URL."""
    return str(value)


converter.register_structure_hook(URL, structure_url_hook)
converter.register_unstructure_hook(URL, unstructure_url_hook)


def structure_datetime_hook(value: str, type: type) -> datetime:
    """Cattrs converter for URL."""
    return datetime.fromisoformat(value)


def unstructure_datetime_hook(value: datetime) -> str:
    """Cattrs converter for URL."""
    return value.isoformat()


converter.register_structure_hook(datetime, structure_datetime_hook)
converter.register_unstructure_hook(datetime, unstructure_datetime_hook)


log = logging.getLogger("invenio_nrp.client.deserialize")


def deserialize_rest_response[T](
    connection: Any,
    json_payload: bytes,
    result_class: type[T],
    etag: Optional[str],
) -> T:
    try:
        if get_origin(result_class) is list:
            arg_type = get_args(result_class)[0]
            return cast(
                "result_class",
                [
                    converter.structure(
                        {
                            **x,
                        },
                        arg_type,
                    )
                    for x in _json.loads(json_payload)
                ],
            )
        ret = converter.structure(
            {
                **_json.loads(json_payload),
                # "context": result_context,
            },
            result_class,
        )
        if hasattr(ret, "_etag"):
            ret._etag = etag
        return ret
    except Exception as e:
        import traceback
        traceback.print_exc()
        log.error("Error validating %s with %s", json_payload, result_class)
        raise e
