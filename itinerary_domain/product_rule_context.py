"""Assemble normalized source contexts for product identity decisions."""

from shared.url_metadata import strip_urls

def _values(row,keys):
    pieces=[]
    if row:
        for key in keys:
            value=row.get(key,"")
            if value:pieces.append(str(value))
        for key in ("includes","notable_sights"):
            value=row.get(key,[])
            if isinstance(value,(list,tuple,set)):pieces.extend(str(item) for item in value if item)
            elif value:pieces.append(str(value))
    return pieces

def product_context(row:dict|None=None,*values:object)->str:return strip_urls(" ".join(_values(row,("raw","display_title","title","original_title","details","description","city"))+[str(v) for v in values if v]))
def product_context_lower(row:dict|None=None,*values:object)->str:return product_context(row,*values).lower()

def product_source_context(row:dict|None=None,*values:object)->str:
    pieces=_values(row,("raw","original_title","details","description","city"))
    if row and not any(piece.strip() for piece in pieces) and row.get("title"):pieces.append(str(row["title"]))
    if not pieces:pieces.extend(str(v) for v in values if v)
    return strip_urls(" ".join(pieces))

def product_source_context_lower(row:dict|None=None,*values:object)->str:return product_source_context(row,*values).lower()

def titleish_source_context(row:dict|None=None,*values:object)->str:
    pieces=[]
    if row:
        pieces.extend(str(row.get(key)) for key in ("display_title","title","original_title") if row.get(key))
        details=str(row.get("details","") or "")
        if details:
            first=next((line.strip() for line in details.replace("\r\n","\n").replace("\r","\n").split("\n") if line.strip()),"");segment=first.split("|",1)[0].strip()
            if segment:pieces.append(segment)
    if values and str(values[0] or "").strip():pieces.append(str(values[0]).split("|",1)[0].strip())
    return strip_urls(" ".join(pieces)).strip()
