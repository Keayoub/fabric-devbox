"""Minimal OneLake helper utilities.

This module intentionally keeps a tiny surface area: a function that reads CSV
content from a file-like object or bytes and tries a sequence of encodings until
one succeeds. It's intentionally dependency-light so it can be imported in
notebooks and simple jobs.
"""
from typing import List, Optional
import io
import pandas as pd


DEFAULT_ENCODINGS: List[str] = ["utf-8", "latin1", "iso-8859-1", "cp1252", "utf-16"]


def read_csv_bytes_with_fallback(raw: bytes, encodings: Optional[List[str]] = None) -> pd.DataFrame:
    """Read CSV bytes into a pandas DataFrame trying multiple encodings.

    Args:
        raw: The raw bytes of the CSV file.
        encodings: Optional list of encodings to try. If not provided, a sensible
            default list is used (utf-8, latin1, iso-8859-1, cp1252, utf-16).

    Returns:
        A pandas DataFrame parsed from the CSV bytes.

    Raises:
        UnicodeDecodeError: If none of the encodings succeed.
        pandas.errors.ParserError: If pandas cannot parse the CSV after decoding.
    """
    encs = encodings or DEFAULT_ENCODINGS
    last_exc = None
    for enc in encs:
        try:
            text = raw.decode(enc)
            return pd.read_csv(io.StringIO(text))
        except UnicodeDecodeError as ude:
            last_exc = ude
            continue
        except Exception as e:
            # It might be a pandas parsing error — surface it to the caller.
            raise

    # If we exit the loop, raise the last Unicode error to indicate decoding failed.
    if last_exc:
        raise last_exc


__all__ = ["read_csv_bytes_with_fallback", "DEFAULT_ENCODINGS"]
