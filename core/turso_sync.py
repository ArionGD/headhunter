import os
import logging
import threading
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)

TURSO_URL = os.environ.get("TURSO_DATABASE_URL", "https://sea-hunter-db-ariongd.aws-ap-south-1.turso.io")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3ODczODk1ODcsImlkIjoiMDFhMDI4YjctZWIwMS03NTFkLTkxMDYtZmUxOWIzYWQ5MmM4Iiwia2lkIjoiY0JLYmtMUV9YbENBTHZfbWhXU3NYamhPb000aWluWnRGdnN4ZTI1R2E2RSIsInJpZCI6IjY5OTkxNDM4LTg1MWUtNGRkMy05ZTNhLTAxYzAzNGJiOGU2NiJ9.48OSFkIehpdij2m9ktncowUXjv0aDuQkTo72Wv1srKfFr3LFO9QeAHsPtYb-e4rJAQdwK1Ma2Lubf_UP8xVDDw")

def get_turso_client():
    if not TURSO_URL or not TURSO_TOKEN:
        return None
    try:
        import libsql_client
        clean_url = TURSO_URL.replace("libsql://", "https://")
        return libsql_client.create_client_sync(url=clean_url, auth_token=TURSO_TOKEN)
    except Exception as e:
        logger.warning(f"Failed to initialize Turso client: {e}")
        return None

def init_turso_schema():
    client = get_turso_client()
    if not client:
        return
    try:
        # 1. Leads Table
        client.execute("""
        CREATE TABLE IF NOT EXISTS turso_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            title TEXT,
            organization TEXT,
            email TEXT,
            phone TEXT,
            location TEXT,
            linkedin_url TEXT,
            source TEXT DEFAULT 'manual',
            status TEXT DEFAULT 'discovered',
            inclination_score INTEGER DEFAULT 50,
            inclination_reasons TEXT,
            notes TEXT,
            owner_username TEXT DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. Activity Logs Table
        client.execute("""
        CREATE TABLE IF NOT EXISTS turso_activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            description TEXT,
            target_lead_id INTEGER,
            target_lead_name TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 3. User Metadata & Last Seen Table
        client.execute("""
        CREATE TABLE IF NOT EXISTS turso_user_meta (
            user_id TEXT PRIMARY KEY,
            role TEXT DEFAULT 'user',
            display_name TEXT,
            last_seen TEXT,
            last_ip TEXT,
            last_device TEXT,
            last_action TEXT
        );
        """)

        client.close()
        logger.info("Turso schema initialized successfully with logs & meta.")
    except Exception as e:
        logger.error(f"Turso schema init error: {e}")

def push_lead_to_turso(lead):
    def _push():
        client = get_turso_client()
        if not client:
            return
        try:
            check_sql = "SELECT id FROM turso_leads WHERE name = ? AND owner_username = ?;"
            res = client.execute(check_sql, [lead.name, lead.owner_username])
            if res.rows:
                turso_id = res.rows[0][0]
                update_sql = """
                UPDATE turso_leads SET
                    title = ?, organization = ?, email = ?, phone = ?,
                    location = ?, linkedin_url = ?, source = ?, status = ?,
                    inclination_score = ?, inclination_reasons = ?, notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?;
                """
                client.execute(update_sql, [
                    lead.title, lead.organization, lead.email, lead.phone,
                    lead.location, lead.linkedin_url, lead.source, lead.status,
                    lead.inclination_score, lead.inclination_reasons, lead.notes,
                    turso_id
                ])
            else:
                insert_sql = """
                INSERT INTO turso_leads (
                    name, title, organization, email, phone,
                    location, linkedin_url, source, status,
                    inclination_score, inclination_reasons, notes, owner_username
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """
                client.execute(insert_sql, [
                    lead.name, lead.title, lead.organization, lead.email, lead.phone,
                    lead.location, lead.linkedin_url, lead.source, lead.status,
                    lead.inclination_score, lead.inclination_reasons, lead.notes, lead.owner_username
                ])
            client.close()
        except Exception as e:
            logger.error(f"Failed pushing lead to Turso: {e}")

    threading.Thread(target=_push, daemon=True).start()

def push_activity_log_to_turso(log_entry):
    def _push():
        client = get_turso_client()
        if not client:
            return
        try:
            insert_sql = """
            INSERT INTO turso_activity_logs (
                user_id, action, description, target_lead_id, target_lead_name, ip_address
            ) VALUES (?, ?, ?, ?, ?, ?);
            """
            client.execute(insert_sql, [
                log_entry.user_id, log_entry.action, log_entry.description,
                log_entry.target_lead_id, log_entry.target_lead_name, log_entry.ip_address
            ])
            client.close()
        except Exception as e:
            logger.error(f"Failed pushing activity log to Turso: {e}")

    threading.Thread(target=_push, daemon=True).start()

def push_user_meta_to_turso(meta):
    def _push():
        client = get_turso_client()
        if not client:
            return
        try:
            seen_str = meta.last_seen.isoformat() if meta.last_seen else None
            upsert_sql = """
            INSERT INTO turso_user_meta (
                user_id, role, display_name, last_seen, last_ip, last_device, last_action
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                role = excluded.role,
                display_name = excluded.display_name,
                last_seen = excluded.last_seen,
                last_ip = excluded.last_ip,
                last_device = excluded.last_device,
                last_action = excluded.last_action;
            """
            client.execute(upsert_sql, [
                meta.user_id, meta.role, meta.display_name, seen_str,
                meta.last_ip, meta.last_device, meta.last_action
            ])
            client.close()
        except Exception as e:
            logger.error(f"Failed pushing user meta to Turso: {e}")

    threading.Thread(target=_push, daemon=True).start()

def sync_from_turso():
    def _sync():
        client = get_turso_client()
        if not client:
            return
        try:
            from core.models import Lead, UserMetaTracker
            # 1. Sync Leads
            res = client.execute("SELECT name, title, organization, email, phone, location, linkedin_url, source, status, inclination_score, inclination_reasons, notes, owner_username FROM turso_leads;")
            for row in res.rows:
                name, title, org, email, phone, loc, linkedin, src, status, score, reasons, notes, owner = row
                if not Lead.objects.filter(name=name, owner_username=owner).exists():
                    Lead.objects.create(
                        name=name,
                        title=title,
                        organization=org,
                        email=email,
                        phone=phone or '',
                        location=loc,
                        linkedin_url=linkedin or '',
                        source=src or 'manual',
                        status=status or 'discovered',
                        inclination_score=score or 50,
                        inclination_reasons=reasons,
                        notes=notes,
                        owner_username=owner or 'admin'
                    )

            # 2. Sync Meta
            try:
                res_meta = client.execute("SELECT user_id, role, display_name, last_seen, last_ip, last_device, last_action FROM turso_user_meta;")
                for r in res_meta.rows:
                    uid, role, dname, seen_val, ip, dev, act = r
                    parsed_seen = parse_datetime(seen_val) if (seen_val and isinstance(seen_val, str)) else None
                    UserMetaTracker.objects.update_or_create(
                        user_id=uid,
                        defaults={
                            'role': role or 'user',
                            'display_name': dname,
                            'last_seen': parsed_seen,
                            'last_ip': ip,
                            'last_device': dev,
                            'last_action': act
                        }
                    )
            except Exception as e:
                logger.warning(f"Meta sync error: {e}")

            client.close()
            logger.info("Synced data from Turso Cloud into local database.")
        except Exception as e:
            logger.error(f"Error syncing from Turso: {e}")

    threading.Thread(target=_sync, daemon=True).start()

def dump_all_leads_to_turso():
    client = get_turso_client()
    if not client:
        return
    try:
        init_turso_schema()
        from core.models import Lead
        for lead in Lead.objects.all():
            check_sql = "SELECT id FROM turso_leads WHERE name = ? AND owner_username = ?;"
            res = client.execute(check_sql, [lead.name, lead.owner_username])
            if res.rows:
                turso_id = res.rows[0][0]
                update_sql = """
                UPDATE turso_leads SET
                    title = ?, organization = ?, email = ?, phone = ?,
                    location = ?, linkedin_url = ?, source = ?, status = ?,
                    inclination_score = ?, inclination_reasons = ?, notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?;
                """
                client.execute(update_sql, [
                    lead.title, lead.organization, lead.email, lead.phone,
                    lead.location, lead.linkedin_url, lead.source, lead.status,
                    lead.inclination_score, lead.inclination_reasons, lead.notes,
                    turso_id
                ])
            else:
                insert_sql = """
                INSERT INTO turso_leads (
                    name, title, organization, email, phone,
                    location, linkedin_url, source, status,
                    inclination_score, inclination_reasons, notes, owner_username
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """
                client.execute(insert_sql, [
                    lead.name, lead.title, lead.organization, lead.email, lead.phone,
                    lead.location, lead.linkedin_url, lead.source, lead.status,
                    lead.inclination_score, lead.inclination_reasons, lead.notes, lead.owner_username
                ])
        client.close()
        print("Successfully synced all local leads into Turso Cloud database!")
    except Exception as e:
        print(f"Error dumping leads to Turso: {e}")