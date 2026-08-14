from fastapi import Depends, Query

from auth.deps import Scope, get_scope
from main import app, _row_to_dict
from repositories.chat_repository import list_chats


@app.get("/api/chats")
def lista(obra_id: int = Query(...), scope: Scope = Depends(get_scope)):
    return [_row_to_dict(c) for c in list_chats(obra_id, scope)]
