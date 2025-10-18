import sqlalchemy as alc
import pandas as pd
from sqlalchemy.dialects.mysql import insert as mysql_insert
from config import cfg


def get_connection():
    url = cfg.get_dbConnection()
    return alc.create_engine(url)


def createDB():
    if checkDBSctructure():
        print(f"[INFO] Database {cfg.db_name} already created with {cfg.db_script}")
        print("[INFO] Skipping to data processing...")
    else:
        try:
            engine = get_connection()
            print(
                f"[INFO] Connection to {cfg.db_host}/{cfg.db_name} for user {cfg.db_user} established successfully."
            )
            with engine.begin() as conn:
                dataSQL = open(cfg.db_script).read()
                statements = dataSQL.split(";")
                for stmt in statements:
                    stmt = stmt.strip()
                    if stmt:
                        conn.execute(alc.text(stmt))
            engine.dispose()
            print(f"[INFO] Database {cfg.db_name} created successfully")
        except Exception as ex:
            print("[ERROR] An error occurred: \n", ex)


def extractTable(table):
    try:
        engine = get_connection()
        with engine.begin() as conn:
            alcTable = alc.Table(table, alc.MetaData(), autoload_with=conn)
            result = conn.execute(alc.select(alcTable))
            rows = [dict(row._mapping) for row in result]
        engine.dispose()
        return rows
    except Exception as ex:
        print(f"[ERROR] An error occurred extracting table {table}: \n", ex)


def extractValues(table_name, target_cols, conditions):
    try:
        engine = get_connection()
        with engine.begin() as conn:
            metadata = alc.MetaData()
            table = alc.Table(table_name, metadata, autoload_with=conn)
            if isinstance(target_cols, str):
                target_cols = [target_cols]
            stmt = alc.select(*[table.c[col] for col in target_cols])
            for col, val in conditions.items():
                stmt = stmt.where(table.c[col] == val)
            result = conn.execute(stmt).fetchone()
        engine.dispose()
        if result:
            if len(target_cols) == 1:
                return result[0]
            else:
                return dict(zip(target_cols, result))
        return None
    except Exception as ex:
        print(
            f"[ERROR] An error occurred extracting data from table {table_name} with conditions {conditions}: \n",
            ex,
        )


def insertData(data, batch_size=200000):
    try:
        engine = get_connection()
        metadata = alc.MetaData()
        with engine.begin() as conn:
            inspector = alc.inspect(conn)
            db_tables = set(inspector.get_table_names())

            for table_name, values in data.items():
                if table_name not in db_tables:
                    print(
                        f"[INFO] Table '{table_name}' does not exist in the database."
                    )
                    continue

                if not values:
                    print(
                        f"[INFO] No data to insert for table '{table_name}'. Skipping."
                    )
                    continue

                print(
                    f"[INFO] Trying to insert values into table '{table_name}' ({len(values)} records)"
                )

                on_dup_method = cfg.onDuplicateDBrule.get(table_name, "ignore")
                on_dup_criteria = cfg.onDuplicateDBbase.get(table_name, [])
                id_col = cfg.idMapping.get(table_name)

                table = alc.Table(table_name, metadata, autoload_with=conn)
                rows = values if isinstance(values, list) else [values]

                if on_dup_method == "ignore":
                    insert_statement = mysql_insert(table).prefix_with("IGNORE")
                    total = len(rows)
                    inserted = 0

                    for i in range(0, total, batch_size):
                        batch = rows[i : i + batch_size]
                        if batch:
                            try:
                                result = conn.execute(insert_statement, batch)
                                inserted += result.rowcount or 0
                                skipped = len(batch) - (result.rowcount or 0)
                                print(
                                    f"[INFO] Batch {i}-{i+len(batch)-1}: inserted={inserted}, skipped_duplicates={skipped}"
                                )

                            except Exception as ex:
                                print(
                                    f"[ERROR] Failed to insert batch {i}-{i + len(batch) - 1}"
                                )
                                print(f"[ERROR] Batch sample: {batch[:3]} ...")
                                raise RuntimeError(
                                    f"Insert failed for table '{table_name}' on batch {i}-{i + len(batch) - 1}: {ex}"
                                ) from ex
                elif on_dup_method == "update" and on_dup_criteria:
                    # only non-key columns will be updated (key columns are defined in the schema) not with NULL!!
                    non_key_cols = [
                        col.name
                        for col in table.columns
                        if col.name not in on_dup_criteria and col.name != id_col
                    ]
                    insert_statement = mysql_insert(table)
                    update_map = {
                        c: alc.func.coalesce(insert_statement.inserted[c], table.c[c])
                        for c in non_key_cols
                    }

                    upsert_statement = insert_statement.on_duplicate_key_update(
                        **update_map
                    )
                    total = len(rows)

                    total_affected = 0

                    for i in range(0, total, batch_size):
                        batch = rows[i : i + batch_size]
                        if batch:
                            res = conn.execute(upsert_statement, batch)
                            rc = res.rowcount or 0
                            total_affected += rc
                            # MySQL returns rowcount as the total number of affected rows (inserted + updated)
                            # We cannot distinguish inserted vs updated in batch mode, so we report total affected
                            print(
                                f"[INFO] Batch {i}-{i+len(batch)-1}: affected={rc}"
                            )

                    print(
                        f"[INFO] '{table_name}': total affected rows={total_affected}"
                    )

                else:
                    total = len(rows)
                    inserted = 0

                    for i in range(0, total, batch_size):
                        batch = rows[i : i + batch_size]
                        if batch:
                            try:
                                result = conn.execute(table.insert(), batch)
                                inserted += result.rowcount or 0
                                print(
                                    f"[INFO] Batch {i}-{i+len(batch)-1}: inserted={inserted}"
                                )
                            except Exception as ex:
                                print(
                                    f"[ERROR] Failed to insert batch {i}-{i + len(batch) - 1}"
                                )
                                print(f"[ERROR] Batch sample: {batch[:3]} ...")
                                raise RuntimeError(
                                    f"Insert failed for table '{table_name}' on batch {i}-{i + len(batch) - 1}: {ex}"
                                ) from ex
        engine.dispose()
        print("[INFO] All data inserted successfully")

    except Exception as ex:
        print("[ERROR] Error during insert:", ex)
        raise


def checkDB(engine):
    inspector = alc.inspect(engine)
    print("[INFO] Current DB:", engine.url.database)
    for table_name in inspector.get_table_names():
        print("[INFO] Table:", table_name)


def checkDBSctructure():
    try:
        engine = get_connection()
        metadata = alc.MetaData()
        metadata.reflect(bind=engine)
        schema = {}
        for table_name, table in metadata.tables.items():
            schema[table_name] = [col.name for col in table.columns]

        modelStructure = cfg.db_Skeleton()

        # Check if database has any tables
        if not schema:
            print("[INFO] Database exists but has no tables")
            return False

        # Check if all required tables exist
        if schema.keys() != modelStructure.keys():
            print(
                f"[INFO] Schema mismatch - Expected tables: {set(modelStructure.keys())}, Found: {set(schema.keys())}"
            )
            return False

        # Check if all tables have correct columns
        for key in schema:
            if set(schema[key]) != set(modelStructure[key]):
                print(
                    f"[INFO] Column mismatch in table '{key}' - Expected: {set(modelStructure[key])}, Found: {set(schema[key])}"
                )
                return False

        print("[INFO] Database schema is correct")
        return True

    except Exception as ex:
        url = cfg.get_dbConnection()
        print(f"[INFO] Database does not exist or cannot be accessed: {ex}")
        return False
