import io
import zipfile
import pandas as pd

from streamlit.runtime.uploaded_file_manager import UploadedFile


def read_first_csv_from_zip(
    uploaded_file: UploadedFile, encoding: str = "utf-8", **read_csv_kwargs
):
    """
    Reads the first .csv file found inside an uploaded .zip and returns (df, csv_name).

    uploaded_file: Streamlit UploadedFile (or anything with .read()).
    encoding: fallback text encoding for pandas if it needs it.
    **read_csv_kwargs: forwarded to pd.read_csv
    """
    raw = uploaded_file.read()

    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        csv_names = [name for name in zf.namelist() if name.lower().endswith(".csv")]

        if not csv_names:
            raise ValueError("No .csv file found inside the zip.")

        csv_name = csv_names[0]

        with zf.open(csv_name) as f:
            df = pd.read_csv(f, encoding=encoding, **read_csv_kwargs)

    return df, csv_name
