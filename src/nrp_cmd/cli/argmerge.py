"""Tools to wrap function, merging all arguments."""

import inspect
import sys
from collections.abc import Callable
from typing import Optional


def merge_arguments(
    wrapping_function: Callable,
    orig_function: Callable,
    param_check: Optional[Callable] = None,
    wrapper_async: bool = True,
    orig_async: bool = True,
) -> Callable:
    """Merge the arguments of two functions into a new function.
    
    For typer, we need to have type annotations for the arguments.
    The function that goes to typer needs to have the arguments
    with the correct types in inspect.signature.
    
    This does not work just with __annotation__ because it does not
    get propagated to the signature.
    
    We can not use functools with partial as the arguments are not
    correctly propagated either.
    
    The solution is to generate a new function with the correct
    signature and inside it call the wrapper with the correct
    arguments. This is done by generating the code for the new
    function, executing it and returning the generated function.
    """
    if not param_check:
        param_check = lambda name, param: True

    # these are the params that will be passed as globals to the generated
    # function
    locs: dict = {
        **globals(),
        "wrapper": wrapping_function,
    }
    fn = orig_function.__name__ + "_" + wrapping_function.__name__

    # synchronous or asynchronous definition
    generated_code = (
        ["async def " + fn + "(*,"] if wrapper_async else ["def " + fn + "(*,"]
    )

    # get which params should be generated and which should be ignored
    params_to_generate: dict[str, inspect.Parameter] = {}
    params_to_ignore: set = set()

    wrapping_sig = inspect.signature(wrapping_function, eval_str=True)
    orig_sig = inspect.signature(orig_function, eval_str=True)

    _gather_params(wrapping_sig, params_to_generate, params_to_ignore, param_check)
    _gather_params(orig_sig, params_to_generate, params_to_ignore, param_check)

    # for each param that should be generated, generate the signature
    # we do not want to have any sort of injection, so we do not pass
    # the types literaly, we pass the evaluated type as a variable in the
    # globals
    for param_name, param in params_to_generate.items():
        param_name_type = f"{param_name}_type"
        locs[param_name_type] = param.annotation

        if param.default is inspect.Parameter.empty:
            generated_code.append(f"    {param_name}: {param_name_type},")
        else:
            param_name_default = f"{param_name}_default"
            locs[param_name_default] = param.default
            generated_code.append(
                f"    {param_name}: {param_name_type} = {param_name_default},"
            )

    # now generate function body
    generated_code.append("):")
    if wrapper_async:
        if orig_async:
            # if the result function is async and wrapped as well, await
            generated_code.append("    return await wrapper(")
        else:
            # if the wrapper is sync, simple return
            generated_code.append("    return wrapper(")
    else:
        if orig_async:
            # if the result function is sync and wrapper async, run it in asyncio
            generated_code.append("    from asyncio import run as asyncio_run")
            generated_code.append("    return asyncio_run(wrapper(")
        else:
            # sync in sync is a plain call
            generated_code.append("    return wrapper(")

    # just pass the params as they are
    for param_name in params_to_generate:
        generated_code.append(f"        {param_name}={param_name},")

    # and for each ignored, pass None
    for param_name in params_to_ignore:
        generated_code.append(f"        {param_name}=None,")

    # close the call
    if not wrapper_async and orig_async:
        generated_code.append("    ))")
    else:
        generated_code.append("    )")

    # exec the code and get the function
    try:
        exec("\n".join(generated_code), locs, locs)
    except Exception as e:
        print("\n".join(generated_code), file=sys.stderr)
        raise RuntimeError(
            f"Failed to generate code from {orig_function} wrapped by {wrapping_function}"
        ) from e
    ret_func = locs[fn]
    return ret_func


def _gather_params(
    sig: inspect.Signature,
    params_to_generate: dict[str, inspect.Parameter],
    params_to_ignore: set[str],
    param_check: Callable[[str, inspect.Parameter], bool],
) -> None:
    """Gather the parameters that should be generated and those that should be ignored.
    
    Only keyword arguments are supported.
    """
    for name, param in sig.parameters.items():
        if name in params_to_generate:
            continue
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            # ignore variable parameters
            continue
        if param.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            raise ValueError(f"Positional arguments are not supported {name}: {param}")
        if param.annotation is inspect.Parameter.empty:
            continue
        if not param_check(name, param):
            params_to_ignore.add(name)
            continue
        params_to_generate[name] = param


if __name__ == "__main__":
    from pathlib import Path
    from typing import Annotated

    import typer

    from nrp_cmd.cli.base import async_command

    @async_command
    async def accept_request(
        *,
        request_id: Annotated[str, typer.Argument(help="Request type ID")],
        output: Annotated[
            Optional[Path], typer.Option("-o", help="Save the output to a file")
        ] = None,
        output_format: Annotated[
            Optional[str],
            typer.Option("-f", help="The format of the output"),
        ] = None,
        repository: Annotated[
            Optional[str], typer.Option(help="Repository alias")
        ] = None,
    ) -> None:
        pass
