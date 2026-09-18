"""Readable V2 solution with consistent decision-log schema."""

def decision(entity, item_id, field, raw, action, clean, reason):
    return {"entity":entity,"id":item_id,"field":field,"raw":raw,
            "action":action,"clean":clean,"reason":reason}

def normalize_text(value):
    if value is None: return None
    text=str(value).strip()
    return text or None

def normalize_email(value):
    email=normalize_text(value)
    if not email: return None
    email=email.lower()
    if " " in email or email.count("@") != 1: return None
    local,domain=email.split("@")
    if not local or "." not in domain or domain.startswith(".") or domain.endswith("."): return None
    return email

def parse_non_negative_float(value):
    try: number=float(value)
    except (TypeError,ValueError): return None
    return number if number >= 0 else None

def parse_positive_int(value):
    if isinstance(value,bool) or (isinstance(value,float) and not value.is_integer()): return None
    try:
        text=str(value).strip()
        if "." in text: return None
        number=int(text)
    except (TypeError,ValueError): return None
    return number if number > 0 else None

def clean_users(rows):
    clean=[]; rejected=[]; decisions=[]; seen=set()
    for index,row in enumerate(rows):
        raw_id=row.get("user_id"); uid=normalize_text(raw_id)
        reason="missing user_id" if not uid else "duplicate user_id" if uid in seen else None
        if reason:
            rejected.append({"raw_index":index,"row":row,"reason":reason})
            decisions.append(decision("users",uid,"user_id",raw_id,"DROP",None,reason)); continue
        out=row.copy(); out["user_id"]=uid
        for field in ("name","city"):
            raw=row.get(field); new=normalize_text(raw); out[field]=new
            if new is None and raw is not None: decisions.append(decision("users",uid,field,raw,"NULL",None,"empty text"))
            elif new != raw: decisions.append(decision("users",uid,field,raw,"FIX",new,"trim whitespace"))
        raw=row.get("email"); new=normalize_email(raw); out["email"]=new
        if new is None and raw is not None: decisions.append(decision("users",uid,"email",raw,"NULL",None,"invalid email"))
        elif new != raw: decisions.append(decision("users",uid,"email",raw,"FIX",new,"trim/lower email"))
        clean.append(out); seen.add(uid)
    return clean,rejected,decisions

def clean_products(rows):
    clean=[]; rejected=[]; decisions=[]; seen=set()
    for index,row in enumerate(rows):
        raw_id=row.get("product_id"); pid=normalize_text(raw_id)
        raw_name=row.get("name"); name=normalize_text(raw_name)
        raw_price=row.get("price"); price=parse_non_negative_float(raw_price)
        if not pid: field,raw,reason="product_id",raw_id,"missing product_id"
        elif pid in seen: field,raw,reason="product_id",raw_id,"duplicate product_id"
        elif not name: field,raw,reason="name",raw_name,"missing name"
        elif price is None: field,raw,reason="price",raw_price,"invalid price"
        else: reason=None
        if reason:
            rejected.append({"raw_index":index,"row":row,"reason":reason})
            decisions.append(decision("products",pid,field,raw,"DROP",None,reason)); continue
        out=row.copy(); out.update(product_id=pid,name=name,price=price)
        if name != raw_name: decisions.append(decision("products",pid,"name",raw_name,"FIX",name,"trim whitespace"))
        if price != raw_price: decisions.append(decision("products",pid,"price",raw_price,"FIX",price,"numeric conversion"))
        clean.append(out); seen.add(pid)
    return clean,rejected,decisions

def clean_transactions(rows):
    clean=[]; rejected=[]; decisions=[]; seen=set()
    for index,row in enumerate(rows):
        raw_id=row.get("tx_id"); tid=normalize_text(raw_id)
        raw_qty=row.get("quantity"); qty=parse_positive_int(raw_qty)
        if not tid: field,raw,reason="tx_id",raw_id,"missing tx_id"
        elif tid in seen: field,raw,reason="tx_id",raw_id,"duplicate tx_id"
        elif qty is None: field,raw,reason="quantity",raw_qty,"invalid quantity"
        else: reason=None
        if reason:
            rejected.append({"raw_index":index,"row":row,"reason":reason})
            decisions.append(decision("transactions",tid,field,raw,"DROP",None,reason)); continue
        out=row.copy(); out.update(tx_id=tid,user_id=normalize_text(row.get("user_id")),product_id=normalize_text(row.get("product_id")),quantity=qty)
        if qty != raw_qty: decisions.append(decision("transactions",tid,"quantity",raw_qty,"FIX",qty,"integer conversion"))
        clean.append(out); seen.add(tid)
    return clean,rejected,decisions
