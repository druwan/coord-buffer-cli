import psycopg

from coord_buffer.config import DB_PARAMS


def create_tmas_table():
    with psycopg.connect(**DB_PARAMS) as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        cursor.execute("""
            CREATE TABLE tmas (
                id SERIAL PRIMARY KEY,
                name_of_area VARCHAR(255) NOT NULL,
                geometry GEOMETRY(POLYGON, 4326) NOT NULL,
                wef DATE NOT NULL,
                type_of_area VARCHAR(50),
                position_indicator VARCHAR(50),
                date_time_of_chg TIMESTAMP,
                name_of_operator VARCHAR(255),
                origin VARCHAR(50),
                location VARCHAR(255),
                upper_limit VARCHAR(50),
                lower_limit VARCHAR(50),
                comment_1 TEXT,
                comment_2 TEXT,
                quality VARCHAR(50),
                crc_id VARCHAR(50),
                crc_pos VARCHAR(50),
                crc_tot VARCHAR(50),
                msid INTEGER,
                idnr INTEGER,
                mi_style TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_name_wef UNIQUE (name_of_area, wef)
            );
            CREATE INDEX tmas_geometry_idx ON tmas USING GIST (geometry);
            CREATE INDEX tmas_wef_idx ON tmas (wef);
        """)
        conn.commit()


if __name__ == "__main__":
    create_tmas_table()
