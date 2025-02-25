import math

# Constants
MAX_UPLOAD_OBJECT_SIZE = 5 * 1024**4           # 5 TiB
MAX_UPLOAD_PARTS = 10_000
MIN_UPLOAD_PART_SIZE = 5 * 1024 * 1024         # 5 MiB
MAX_UPLOAD_PART_SIZE = 5 * 1024**3            # 5 GiB

MINIMAL_DOWNLOAD_PART_SIZE = 1024 * 1024  # 1 MiB
MAXIMAL_DOWNLOAD_PARTS = 10_000


def adjust_upload_multipart_params(size: int, parts: int | None =None, part_size: int | None=None) -> tuple[int, int]:
    """Get multipart params consistent with AWS multipart upload constraints.
    
    Given the total 'size' of an S3 object (in bytes), and optionally
    the desired 'parts' (number of parts) and/or 'part_size' (bytes),
    return a tuple (parts, part_size) that satisfy AWS multipart
    upload constraints.

    AWS Constraints:
    - Max object size: 5 TiB
    - Max number of parts: 10,000
    - Part sizes between 5 MiB and 5 GiB (except the last part can be smaller)
    """
    # 1. Validate the total size
    if size < 0:
        raise ValueError("Size cannot be negative.")
    if size == 0:
        # Edge case: a zero-byte object can be uploaded in a single part
        return (1, 0)  # 0-byte part is valid in practice for a zero-byte file

    if size > MAX_UPLOAD_OBJECT_SIZE:
        raise ValueError(f"Size exceeds maximum S3 object size of {MAX_UPLOAD_OBJECT_SIZE} bytes (5 TiB).")

    # Helper to clamp a part_size within valid range
    def clamp_part_size(ps: int) -> int:
        return max(MIN_UPLOAD_PART_SIZE, min(ps, MAX_UPLOAD_PART_SIZE))

    # We will compute final_parts and final_part_size in a systematic way.
    # Start with any user-provided values, but adjust them to satisfy constraints.

    # Case A: If both parts and part_size are provided
    if parts is not None and part_size is not None:
        # Ensure parts is within [1, 10_000]
        if parts < 1 or parts > MAX_UPLOAD_PARTS:
            raise ValueError(f"'parts' must be in the range [1, {MAX_UPLOAD_PARTS}].")

        # Clamp part_size into [5 MiB, 5 GiB]
        part_size = clamp_part_size(part_size)

        # Check how many parts would actually be needed if we use this part_size
        needed_parts = math.ceil(size / part_size)

        if needed_parts > MAX_UPLOAD_PARTS:
            raise ValueError(
                f"With part_size={part_size} bytes, you would need {needed_parts} parts, "
                f"which exceeds the max of {MAX_UPLOAD_PARTS}."
            )

        if needed_parts != parts:
            parts = needed_parts

        return (parts, part_size)

    # Case B: If only 'parts' is provided
    elif parts is not None:
        if parts < 1 or parts > MAX_UPLOAD_PARTS:
            raise ValueError(f"'parts' must be in the range [1, {MAX_UPLOAD_PARTS}].")

        # Compute the part_size needed for that many parts
        rough_part_size = math.ceil(size / parts)

        # Clamp it to valid range
        part_size_clamped = clamp_part_size(rough_part_size)

        # Recompute the number of parts with the clamped size
        final_parts = math.ceil(size / part_size_clamped)

        if final_parts > MAX_UPLOAD_PARTS:
            raise ValueError(
                f"Requested {parts} parts but cannot satisfy with AWS limits. "
                "Try fewer parts or do not specify 'parts'."
            )

        return (final_parts, part_size_clamped)

    # Case C: If only 'part_size' is provided
    elif part_size is not None:
        # Clamp the requested part_size to [5 MiB, 5 GiB]
        part_size_clamped = clamp_part_size(part_size)

        # Calculate how many parts that implies
        final_parts = math.ceil(size / part_size_clamped)

        if final_parts > MAX_UPLOAD_PARTS:
            # We need to increase part_size to reduce the number of parts
            # part_size_needed >= size / MAX_PARTS
            new_part_size = math.ceil(size / MAX_UPLOAD_PARTS)

            # Clamp again
            new_part_size = clamp_part_size(new_part_size)
            final_parts = math.ceil(size / new_part_size)

            if final_parts > MAX_UPLOAD_PARTS:
                raise ValueError(
                    "Cannot upload within AWS constraints even after adjusting part_size. "
                    f"size={size}, part_size_requested={part_size}, new_part_size={new_part_size}, parts={final_parts}"
                )

            return (final_parts, new_part_size)
        else:
            return (final_parts, part_size_clamped)

    # Case D: Neither 'parts' nor 'part_size' provided
    else:
        # Strategy: pick the maximum possible number of parts up to 10,000
        # i.e., start with the smallest valid part size (5 MiB),
        # and only increase it if we exceed 10,000 parts.

        max_parts_possible = math.ceil(size / MIN_UPLOAD_PART_SIZE)

        if max_parts_possible <= MAX_UPLOAD_PARTS:
            # We can use the minimum part size of 5 MiB and still not exceed 10,000 parts
            final_parts = max_parts_possible
            chosen_part_size = MIN_UPLOAD_PART_SIZE
        else:
            # 5 MiB parts would create too many parts (>10,000).
            # We must increase part_size enough to reduce the count to 10,000 or fewer.
            chosen_part_size = math.ceil(size / MAX_UPLOAD_PARTS)
            chosen_part_size = clamp_part_size(chosen_part_size)  # still enforce [5MiB..5GiB]

            final_parts = math.ceil(size / chosen_part_size)
            if final_parts > MAX_UPLOAD_PARTS:
                raise ValueError(
                    "Cannot satisfy AWS multipart constraints with 10,000 parts. "
                    f"Size={size}, chosen_part_size={chosen_part_size}, parts={final_parts}"
                )

        return (final_parts, chosen_part_size)


def adjust_download_multipart_params(
    size: int,
    parts: int | None = None,
    part_size: int | None = None
) -> tuple[int, int]:
    """Adjust download multipart parameters to fit within constraints.
    
    Computes and returns (final_part_size, final_parts) such that:
      - final_part_size >= MINIMAL_PART_SIZE
      - final_parts <= MAXIMAL_PARTS
      - size fits into final_parts * final_part_size
      - Prefers more parts (smaller part_size) when possible.
    
    :param size: Total size we want to split.
    :param maximal_parts: The largest allowed number of parts.
    :param parts: Desired (or initial) number of parts, can be None.
    :param part_size: Desired (or initial) size of each part, can be None.

    :return (final_part_size, final_parts)

    """

    # Helper that clamps final_part_size to respect minimal size and ensures final_parts <= MAXIMAL_PARTS
    def compute_with_part_size(psize: int) -> tuple[int, int]:
        """Enforce constraints on part_size and compute parts needed."""
        # Enforce minimal part size
        psize = max(psize, MINIMAL_DOWNLOAD_PART_SIZE)
        # Compute parts needed
        needed_parts = math.ceil(size / psize)
        # If we exceed the max, bump the part size up to reduce parts
        if needed_parts > MAXIMAL_DOWNLOAD_PARTS:
            psize = math.ceil(size / MAXIMAL_DOWNLOAD_PARTS)
            needed_parts = math.ceil(size / psize)
        return psize, needed_parts

    # CASE 1: If BOTH part_size and parts are None => 
    #         start from the minimal part size (=> maximum number of parts),
    #         and adjust if that exceeds MAXIMAL_PARTS.
    if part_size is None and parts is None:
        return compute_with_part_size(MINIMAL_DOWNLOAD_PART_SIZE)

    # CASE 2: If part_size is given but parts is None => 
    #         rely on that part_size, adjust if we exceed constraints.
    if part_size is not None and parts is None:
        return compute_with_part_size(part_size)

    # CASE 3: If part_size is None but parts is given => 
    #         we pick the part_size that roughly matches the desired parts, 
    #         then adjust to constraints.
    if part_size is None and parts is not None:
        # The part size that (ideally) yields exactly 'parts'
        candidate_size = math.floor(size / parts)
        if candidate_size < 1:
            # edge case: if parts > size, candidate_size can be 0 => clamp to 1 or minimal
            candidate_size = 1
        return compute_with_part_size(candidate_size)

    # CASE 4: If BOTH are given => the question doesn't define a perfect tie-break. 
    #         We'll treat 'part_size' as the stronger hint (since it directly 
    #         influences how big each chunk is). Then we adjust if needed.
    #         'parts' is effectively ignored except in commentary or debugging.
    return compute_with_part_size(part_size or MINIMAL_DOWNLOAD_PART_SIZE)


# -------------- TEST EXAMPLES ----------------
if __name__ == "__main__":
    # Example usage
    total_size = 50 * 1024 * 1024  # 50 MB

    # No parts or part_size specified
    p, ps = adjust_upload_multipart_params(total_size)
    print("No hints:", p, ps)

    # Only parts specified
    p, ps = adjust_upload_multipart_params(total_size, parts=2)
    print("Only parts=2:", p, ps)

    # Only part_size specified
    p, ps = adjust_upload_multipart_params(total_size, part_size=5 * 1024 * 1024)  # 5 MB
    print("Only part_size=5MB:", p, ps)

    # Both parts and part_size specified
    p, ps = adjust_upload_multipart_params(total_size, parts=3, part_size=6 * 1024 * 1024)
    print("parts=3, part_size=6MB:", p, ps)
