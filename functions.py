from keyboards import *


async def get_accessed_ids(db_connection, user_id):
    cursor = await db_connection.execute(
        "SELECT user_id FROM user WHERE user_id = ?", (user_id,)
    )
    accessed_id = await cursor.fetchone()
    await cursor.close()
    return accessed_id is not None


async def check_user_tasks(db_connection, user_id):
    cursor = await db_connection.execute(
        "SELECT EXISTS(SELECT 1 FROM tasks WHERE TaskParticipants LIKE '%' || ? || '%' LIMIT 1)",
        (user_id,),
    )
    exists = await cursor.fetchone()
    return bool(exists[0])
