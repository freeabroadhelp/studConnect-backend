import os
import csv
import requests
from bs4 import BeautifulSoup
import boto3
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import json
from db import Base, engine, get_db
from sqlalchemy import text, inspect
from models.models import AustraliaScholarship
import psycopg2
from psycopg2.extras import execute_values

load_dotenv()

Base.metadata.create_all(bind=engine)

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL is not set. Please check your environment variables.")

R2_BUCKET = os.environ.get("R2_BUCKET")
R2_ACCESS_KEY = os.environ.get("R2_ACCESS_KEY")
R2_SECRET_KEY = os.environ.get("R2_SECRET_KEY")
R2_ENDPOINT = os.environ.get("R2_ENDPOINT")
R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL")
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend/data/universities_v4.csv")

session = boto3.session.Session()
r2 = session.client(
    service_name="s3",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    endpoint_url=R2_ENDPOINT,
)

def upload_to_r2(url, key):
    try:
        r2.head_object(Bucket=R2_BUCKET, Key=key)
        return f"{R2_PUBLIC_URL}/{key}"
    except r2.exceptions.ClientError as e:
        if int(e.response['Error']['Code']) != 404:
            raise
    resp = requests.get(url)
    if resp.status_code != 200:
        raise Exception(f"Failed to fetch image: {url}")
    r2.put_object(
        Bucket=R2_BUCKET,
        Key=key,
        Body=resp.content,
        ContentType=resp.headers.get("content-type", "application/octet-stream"),
        ACL="public-read"
    )
    return f"{R2_PUBLIC_URL}/{key}"

def ensure_australia_scholarships_table():
    AustraliaScholarship.__table__.create(bind=engine, checkfirst=True)

def import_data():
    data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend/data/australia_scholarships.json")
    with open(data_path, "r") as f:
        data = json.load(f)
    ensure_australia_scholarships_table()
    Base.metadata.create_all(bind=engine)
    with get_db() as db:
        for entry in data:
            obj = AustraliaScholarship(
                university=entry["university"],
                state=entry.get("state"),
                type=entry.get("type"),
                scholarships=entry.get("scholarships", []),
                common_programs=entry.get("common_programs", []),
                updated_at=entry.get("updated_at")
            )
            db.add(obj)
    db.commit()
    db.close()

def upload_all_universities_json_to_postgres():
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend/data/Australian_Universities.json")
    with open(json_path, encoding='utf-8') as f:
        universities = json.load(f)

    PG_CONN = {
        'host': os.environ.get('PGHOST', 'localhost'),
        'port': int(os.environ.get('PGPORT', 5432)),
        'dbname': os.environ.get('PGDATABASE', 'your_db_name'),
        'user': os.environ.get('PGUSER', 'your_db_user'),
        'password': os.environ.get('PGPASSWORD', 'your_db_password')
    }

    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS all_universities (
        id SERIAL PRIMARY KEY,
        name TEXT,
        state TEXT,
        location TEXT,
        type TEXT,
        networks TEXT,
        established INTEGER,
        latest_rankings JSONB,
        official_website TEXT,
        official_email TEXT,
        popular_for_international_students TEXT[],
        levels_offered TEXT[],
        intakes TEXT[],
        mode_of_study TEXT[],
        scholarships_highlight TEXT[],
        tuition_fees_per_year JSONB,
        living_costs_annual_AUD NUMERIC,
        application_fee_range_AUD TEXT,
        international_student_support TEXT[],
        campus_life JSONB,
        admission_requirements JSONB,
        why_choose TEXT[],
        thumbnail_r2 TEXT,
        logo_r2 TEXT,
        UNIQUE(name)
    );
    """

    def to_pg_array(val):
        return val if isinstance(val, list) else []

    rows = []
    for uni in universities:
        rows.append((
            uni.get('name'),
            uni.get('state'),
            uni.get('location'),
            uni.get('type'),
            uni.get('networks'),
            uni.get('established'),
            json.dumps(uni.get('latest_rankings')) if uni.get('latest_rankings') else None,
            uni.get('official_website'),
            uni.get('official_email'),
            to_pg_array(uni.get('popular_for_international_students')),
            to_pg_array(uni.get('levels_offered')),
            to_pg_array(uni.get('intakes')),
            to_pg_array(uni.get('mode_of_study')),
            to_pg_array(uni.get('scholarships_highlight')),
            json.dumps(uni.get('tuition_fees_per_year')) if uni.get('tuition_fees_per_year') else None,
            uni.get('living_costs_annual_AUD'),
            uni.get('application_fee_range_AUD'),
            to_pg_array(uni.get('international_student_support')),
            json.dumps(uni.get('campus_life')) if uni.get('campus_life') else None,
            json.dumps(uni.get('admission_requirements')) if uni.get('admission_requirements') else None,
            to_pg_array(uni.get('why_choose')),
            uni.get('thumbnail_r2'),
            uni.get('logo_r2')
        ))

    INSERT_SQL = """
    INSERT INTO all_universities (
        name, state, location, type, networks, established, latest_rankings, official_website, official_email,
        popular_for_international_students, levels_offered, intakes, mode_of_study, scholarships_highlight,
        tuition_fees_per_year, living_costs_annual_AUD, application_fee_range_AUD, international_student_support,
        campus_life, admission_requirements, why_choose, thumbnail_r2, logo_r2
    ) VALUES %s
    ON CONFLICT (name) DO NOTHING;
    """

    conn = psycopg2.connect(**PG_CONN)
    cur = conn.cursor()
    cur.execute(CREATE_TABLE_SQL)
    execute_values(
        cur, INSERT_SQL, rows,
        template="""(
            %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )"""
    )
    conn.commit()
    cur.close()
    conn.close()
    print("Upload complete.")

def extract_logo_and_thumbnail(website_url):
    """
    Given a university official website, try to extract logo and thumbnail image URLs.
    Returns (logo_url, thumbnail_url) or (None, None) if not found.
    """
    try:
        resp = requests.get(website_url, timeout=10)
        if resp.status_code != 200:
            return None, None
        soup = BeautifulSoup(resp.text, "html.parser")
        # Try to find logo: look for <img> with 'logo' in class or alt or src
        logo = None
        for img in soup.find_all("img"):
            attrs = " ".join([str(img.get("class", "")), str(img.get("alt", "")), str(img.get("src", ""))]).lower()
            if "logo" in attrs:
                logo = img.get("src")
                break
        # Try to find thumbnail: look for <meta property="og:image">
        thumbnail = None
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            thumbnail = og["content"]
        # Make URLs absolute if needed
        def abs_url(url):
            if not url:
                return None
            if url.startswith("http"):
                return url
            if url.startswith("//"):
                return "https:" + url
            return website_url.rstrip("/") + "/" + url.lstrip("/")
        return abs_url(logo), abs_url(thumbnail)
    except Exception as e:
        print(f"Failed to extract logo/thumbnail from {website_url}: {e}")
        return None, None

def upload_to_r2_from_url(url, key, r2, bucket, public_url):
    try:
        r2.head_object(Bucket=bucket, Key=key)
        return f"{public_url}/{key}"
    except r2.exceptions.ClientError as e:
        if int(e.response['Error']['Code']) != 404:
            raise
    resp = requests.get(url)
    if resp.status_code != 200:
        raise Exception(f"Failed to fetch image: {url}")
    r2.put_object(
        Bucket=bucket,
        Key=key,
        Body=resp.content,
        ContentType=resp.headers.get("content-type", "application/octet-stream"),
        ACL="public-read"
    )
    return f"{public_url}/{key}"

def update_all_universities_logo_thumbnail():
    # Load config and R2 client
    R2_BUCKET = os.environ.get("R2_BUCKET")
    R2_ACCESS_KEY = os.environ.get("R2_ACCESS_KEY")
    R2_SECRET_KEY = os.environ.get("R2_SECRET_KEY")
    R2_ENDPOINT = os.environ.get("R2_ENDPOINT")
    R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL")
    session = boto3.session.Session()
    r2 = session.client(
        service_name="s3",
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        endpoint_url=R2_ENDPOINT,
    )

    # Load universities JSON
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend/data/Australian_Universities.json")
    with open(json_path, encoding='utf-8') as f:
        universities = json.load(f)

    # Connect to Postgres
    PG_CONN = {
        'host': os.environ.get('PGHOST', 'localhost'),
        'port': int(os.environ.get('PGPORT', 5432)),
        'dbname': os.environ.get('PGDATABASE', 'your_db_name'),
        'user': os.environ.get('PGUSER', 'your_db_user'),
        'password': os.environ.get('PGPASSWORD', 'your_db_password')
    }
    conn = psycopg2.connect(**PG_CONN)
    cur = conn.cursor()

    # Ensure columns exist before updating
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='all_universities' AND column_name='logo_r2'
            ) THEN
                ALTER TABLE all_universities ADD COLUMN logo_r2 TEXT;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='all_universities' AND column_name='thumbnail_r2'
            ) THEN
                ALTER TABLE all_universities ADD COLUMN thumbnail_r2 TEXT;
            END IF;
        END$$;
    """)
    conn.commit()

    for uni in universities:
        name = uni.get('name')
        website = uni.get('official_website')
        if not website:
            print(f"Skipping {name}: no official_website")
            continue

        print(f"Processing {name} ({website}) ...")
        logo_url, thumb_url = extract_logo_and_thumbnail(website)
        logo_r2_url = None
        thumb_r2_url = None

        if logo_url:
            ext = logo_url.split(".")[-1].split("?")[0][:5]
            key = f"logos/{name.replace(' ','_')}.{ext}"
            try:
                logo_r2_url = upload_to_r2_from_url(logo_url, key, r2, R2_BUCKET, R2_PUBLIC_URL)
                print(f"  Uploaded logo to {logo_r2_url}")
            except Exception as e:
                print(f"  Logo upload failed: {e}")

        if thumb_url:
            ext = thumb_url.split(".")[-1].split("?")[0][:5]
            key = f"thumbnails/{name.replace(' ','_')}.{ext}"
            try:
                thumb_r2_url = upload_to_r2_from_url(thumb_url, key, r2, R2_BUCKET, R2_PUBLIC_URL)
                print(f"  Uploaded thumbnail to {thumb_r2_url}")
            except Exception as e:
                print(f"  Thumbnail upload failed: {e}")

        # Update all_universities table
        cur.execute(
            """
            UPDATE all_universities
            SET logo_r2 = %s, thumbnail_r2 = %s
            WHERE name = %s
            """,
            (logo_r2_url, thumb_r2_url, name)
        )
        conn.commit()

    cur.close()
    conn.close()
    print("All logo/thumbnail updates complete.")

# To run:
update_all_universities_logo_thumbnail()
