# import uvicorn
import os
# from dotenv import load_dotenv

from collections import deque
from datetime import datetime, timedelta
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi_sqlalchemy import DBSessionMiddleware, db
from sqlalchemy.sql import exists
from typing import Optional

from models import Item
from models import Item as ModelItem
from models import to_dict
from schema import Batch

import aiofiles
import json
# import yaml

app = FastAPI()

# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# load_dotenv(os.path.join(BASE_DIR, ".env"))
# app.add_middleware(DBSessionMiddleware, db_url=os.environ["DATABASE_URL"])

db_url = "postgresql+psycopg2://postgres:password@db:5432/disk_db"
app.add_middleware(DBSessionMiddleware, db_url=db_url)


@app.get("/")
async def root():
    return {"message": "Welcome to the disk!"}


@app.post("/imports/")
async def imports(batch_line: str = Form(...), files: Optional[list[UploadFile]] = File(None)):

    batch = json.loads(batch_line)
    # batch = yaml.load(batch_line) to parse extra trailing commas
    pydantic_batch = Batch.parse_obj(batch)

    if files:
        files = iter(files)
    prefix = "/code/app/storage"

    existing_items = db.session.query(Item).all()
    ex_ids = [el.id for el in existing_items]
    ex_paths = [el.url + "/" + el.filename for el in existing_items if el.url]
    ids_to_update, items_to_update = [], []
    paths_to_del = []
    # item_mappings = []

    for item in pydantic_batch.items:
        db_item = ModelItem(
            id=item.id,
            type=item.type,
            parentId=item.parentId,
            url=item.url,
            size=item.size,
            date=pydantic_batch.updateDate
        )

        if item.type == "FOLDER":
            if item.url:
                raise HTTPException(status_code=404, detail="Folders cannot be passed with url")
            elif item.size:
                raise HTTPException(status_code=404, detail="Folders cannot have a size")

        if item.type == "FILE":
            if item.size <= 0:
                raise HTTPException(status_code=404, detail="File size is less than or equal zero")

        try:
            datetime.fromisoformat(batch["updateDate"].replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="UpdateDate not in ISO 8601 format")

        if item.type == "FILE":
            file = next(files)
            path = prefix + item.url + "/" + file.filename
            db_item.filename = file.filename
            if ".." in item.url.split("/"):
                raise HTTPException(status_code=400, detail="Validation failed: incorrect item url")
            if not os.path.exists(prefix + item.url):
                os.makedirs(prefix + item.url)
            async with aiofiles.open(path, "wb") as out_file:
                while content := await file.read(1024):
                    await out_file.write(content)

        if db_item.id not in ex_ids:
            db.session.add(db_item)
        else:
            ids_to_update.append(db_item.id)
            items_to_update.append(db_item)
            if db_item.url and db_item.url + "/" + db_item.filename not in ex_paths:
                paths_to_del.append(prefix + db_item.url + "/" + db_item.filename)
            # item_mappings.append(to_dict(db_item))

    for path in paths_to_del:
        os.remove(path)

    # db.session.bulk_update_mappings(Item, item_mappings)
    db.session.query(Item).filter(Item.id.in_(ids_to_update)).delete()
    db.session.bulk_save_objects(items_to_update)
    db.session.commit()

    return {"Result": "OK"}


@app.get("/download/")
async def download_file(url_and_filename: str):

    prefix = "/code/app/storage"
    path = prefix + url_and_filename

    if os.path.isfile(path) and ".." not in url_and_filename.split("/"):
        return FileResponse(path)

    raise HTTPException(status_code=404, detail="Item not found")


def get_item(item_class, node_idx):

    is_found = db.session.query(exists().where(item_class.id == node_idx)).scalar()

    return to_dict(db.session.query(item_class).filter(item_class.id == node_idx).one()) if is_found else None


def get_children(par_id):

    found = [to_dict(el) for el in db.session.query(Item).filter(Item.parentId == par_id)]

    return found


def calc_size(node, size_dict):

    if node["id"] in size_dict:
        return size_dict[node["id"]]

    if node["type"].name == "FILE":
        node_size = node["size"]
    else:
        node_size = sum([calc_size(child, size_dict) for child in get_children(node["id"])])

    size_dict[node["id"]] = node_size

    return node_size


@app.get("/nodes/")
async def get_nodes(node_id: str):

    item = get_item(Item, node_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    s_dict = {}
    deq = deque([[item]])

    while deq:

        items = deq.popleft()

        for i in range(len(items)):

            children = get_children(items[i]["id"])
            if children:
                deq.append(children)
            items[i]["children"] = children if items[i]["type"].name == "FOLDER" else None

            del items[i]["item_id"]
            del items[i]["filename"]

            items[i]["size"] = calc_size(items[i], s_dict)

    return item


@app.delete("/delete/")
async def delete_nodes(node_id: str):

    item = get_item(Item, node_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    prefix = "/code/app/storage"

    indices, paths = [], []
    deq = deque([[item]])

    while deq:

        items = deq.popleft()

        for i in range(len(items)):

            children = get_children(items[i]["id"])
            if children:
                deq.append(children)

            indices.append(items[i]["item_id"])

            if items[i]["url"]:
                paths.append(prefix + items[i]["url"] + "/" + items[i]["filename"])

    db.session.query(Item).filter(Item.item_id.in_(indices)).delete()
    db.session.commit()

    for path in paths:
        os.remove(path)

    return {"Result": "OK"}


@app.get("/dump/")
async def get_dump():

    dump = [to_dict(el) for el in db.session.query(Item).all()]

    return dump


# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=80, reload=True)
