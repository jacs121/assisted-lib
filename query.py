import requests
from bs4 import BeautifulSoup
import json

headers = {
    "User-Agent": "Mozilla/5.0"
}

def getQueryImage(query: str, limit: int = 1):
    seen = set()
    index = 0
    results = {}
    
    # get image page data from url as a string
    response = requests.get(f"https://www.bing.com/images/search?q={query}", headers=headers)
    
    # format image page data to a soup class
    soup = BeautifulSoup(response.text, "html.parser")

    # loop over all image thumbnail elements
    for a in soup.find_all("a", class_="iusc"):
        if index == limit:
            # stop at the images are at the limit
            break
        try:
            # get the actual image element
            m_json = a.get("m")
            data = json.loads(m_json)
            murl = data.get("murl")

            # check if the element was extracted and is new to us
            if murl:
                if murl in seen:
                    continue
                seen.add(murl)
                
                # only download it if it's an http link
                if not murl.startswith("http"):
                    continue
                
                # get image content response
                response = requests.get(murl, headers=headers, stream=True)
                response.raise_for_status()

                # guess extension (fallback to jpg)
                ext = murl.split(".")[-1].split("?")[0]
                if len(ext) > 5:
                    ext = "jpg"

                # add data to result
                results.update({f"{query}{index}.{ext}": response.content})
                index += 1

        except Exception as e:
            print(f"Failed {murl}: {e}")
    return results