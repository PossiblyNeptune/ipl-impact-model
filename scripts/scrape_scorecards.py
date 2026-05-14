from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .common import BASE_DIR, DEFAULT_RANGES, ensure_dir, scorecard_filename

BASE_URL = "https://www.howstat.com/Cricket/Statistics/IPL/MatchScorecard.asp?MatchCode="


def scrape_scorecards(
    ranges: Optional[Iterable[Tuple[int, int]]] = None,
    output_dir: Path = BASE_DIR,
    base_url: str = BASE_URL,
) -> List[Path]:
    output_dir = ensure_dir(output_dir)
    ranges_to_use = list(ranges) if ranges else list(DEFAULT_RANGES)
    output_files: List[Path] = []

    for start, end in ranges_to_use:
        filename = scorecard_filename(start, end)
        output_path = output_dir / filename
        print(f"Creating {output_path}...")

        writer = pd.ExcelWriter(output_path, engine="openpyxl")
        for match_code in range(start, end + 1):
            url = base_url + str(match_code).zfill(4)
            response = requests.get(url, timeout=60)
            soup = BeautifulSoup(response.text, "html.parser")

            try:
                tables = soup.find_all("table", class_="ScorecardMain")
                if not tables:
                    print(f"  ⚠ No scorecard table found for Match {match_code}")
                    continue

                scorecard_table = tables[0]
                rows = scorecard_table.find_all("tr")
                data = []

                for row in rows:
                    cols = row.find_all("td")
                    cols = [col.get_text(strip=True) for col in cols if col.text.strip()]
                    if cols:
                        data.append(cols)

                if data:
                    df = pd.DataFrame(data)
                    sheet_name = f"Match_{match_code}"
                    df.to_excel(writer, sheet_name=sheet_name[:31], index=False, header=False)
                    print(f"  ✓ Saved Match {match_code}")
                else:
                    print(f"  ⚠ No data found for Match {match_code}")

            except Exception as exc:
                print(f"  ❌ Error processing Match {match_code}: {exc}")

        writer.close()
        output_files.append(output_path)
        print(f"✅ Finished: {output_path}\n")

    return output_files


if __name__ == "__main__":
    scrape_scorecards()
