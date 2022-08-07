import httplib2
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client.service_account import ServiceAccountCredentials

CREDENTIALS_FILE_PATH = "google_api_credentials.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


def find_string_real_type(s: str) -> bool:
    """Monkey hack."""
    try:
        int(s)
        return int
    except Exception:
        pass
    try:
        float(s)
        return float
    except Exception:
        pass
    return str


class Spreadsheet:
    def __init__(
        self,
        spreadsheet_id: str,
        sheet_name: str,
    ):
        self.session = self._get_service_session()
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        try:
            self.get_values()
        except HttpError:
            raise ValueError("Bad Spreadsheet ID or Sheet Name")

    def _get_service_session(self):
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            filename=CREDENTIALS_FILE_PATH,
            scopes=SCOPES,
        ).authorize(httplib2.Http())
        return build("sheets", "v4", http=credentials)

    def get_values(self):
        return (
            self.session.spreadsheets()
            .values()
            .get(
                spreadsheetId=self.spreadsheet_id,
                range=self.sheet_name,
                majorDimension="ROWS",
            )
            .execute()
        )

    def get_spreadsheet_as_df(self) -> pd.DataFrame:
        values = self.get_values()

        # Google API sent only strings. We should convert them to appropriate type.
        df = pd.DataFrame(values["values"][1:], columns=values["values"][0])

        if df.empty:
            return df

        types_info = {}
        for c, x in df.iloc[0].items():
            types_info[c] = find_string_real_type(x)
        df = df.astype(types_info)

        return df

    def push_df_to_spreadsheet(self, df: pd.DataFrame) -> None:
        (
            self.session.spreadsheets()
            .values()
            .update(
                spreadsheetId=self.spreadsheet_id,
                valueInputOption="RAW",
                range=self.sheet_name,
                body={
                    "majorDimension": "ROWS",
                    "values": [list(df.columns)] + df.values.tolist(),
                },
            )
            .execute()
        )
