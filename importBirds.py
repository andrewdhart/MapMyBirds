import pandas as pd
import sqlite3


def import_birds_to_df(csv_path):
    df = pd.read_csv(csv_path)

    # Take care of missing times from imcomplete checklists
    parsed_time = pd.to_datetime(
        df["Time"],
        format="%I:%M %p",
        errors="coerce"
    )

    df["Time"] = parsed_time.dt.strftime("%I:%M %p")
    df.loc[parsed_time.isna(), "Time"] = "12:00 AM"

    df["datetime"] = pd.to_datetime(
        df["Date"].astype(str).str.strip() + " " + df["Time"],
        format="%Y-%m-%d %I:%M %p",
        errors="coerce"
    )

    # Build checklists table
    checklists = (
        df[["datetime", "Latitude", "Longitude", "Location"]]
        .drop_duplicates(subset=["datetime"])
        .sort_values("datetime")
        .reset_index(drop=True)
    )

    # Add unique checklist_id
    checklists.insert(0, "checklist_id", range(1, len(checklists) + 1))

    checklists = checklists.rename(columns={
        "Latitude": "latitude",
        "Longitude": "longitude",
        "Location": "location_name"
    })

    df = df.merge(
        checklists[["checklist_id", "datetime"]],
        on="datetime",
        how="left"
    )


    checklists["datetime"] = checklists["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Build observations table
    observations = df[["Common Name", "Count", "checklist_id"]].copy()

    observations = observations.rename(columns={
        "Common Name": "common_name",
        "Count": "count_text"
    })

    observations["count_num"] = pd.to_numeric(
        observations["count_text"],
        errors="coerce"
    )

    # Add unique observation_id
    observations.insert(0, "observation_id", range(1, len(observations) + 1))

    return checklists, observations


def create_database(checklists, observations, db_path="birds.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Drop tables if they exist
    cur.execute("DROP TABLE IF EXISTS observations")
    cur.execute("DROP TABLE IF EXISTS checklists")

    # Create checklists table
    cur.execute("""
        CREATE TABLE checklists (
            checklist_id INTEGER PRIMARY KEY,
            datetime TEXT NOT NULL UNIQUE,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            location_name TEXT NOT NULL
        )
    """)

    # Create observations table
    cur.execute("""
        CREATE TABLE observations (
            observation_id INTEGER PRIMARY KEY,
            common_name TEXT NOT NULL,
            count_text TEXT,
            checklist_id INTEGER NOT NULL,
            count_num REAL,
            FOREIGN KEY (checklist_id) REFERENCES checklists(checklist_id)
        )
    """)

    # Insert data
    checklists.to_sql("checklists", conn, if_exists="append", index=False)
    observations.to_sql("observations", conn, if_exists="append", index=False)

    # Create indexes
    cur.execute("""
        CREATE INDEX idx_observations_common_name
        ON observations(common_name)
    """)

    cur.execute("""
        CREATE INDEX idx_observations_checklist_id
        ON observations(checklist_id)
    """)

    cur.execute("""
        CREATE INDEX idx_checklists_datetime
        ON checklists(datetime)
    """)

    conn.commit()
    conn.close()

# Import from csv and create sql tables + verify

if __name__ == "__main__":
    checklists, observations = import_birds_to_df("MyEBirdData.csv")

    create_database(checklists, observations, "birds.db")

    print("✅ Database created: birds.db")
    print("Checklists:", len(checklists))
    print("Observations:", len(observations))