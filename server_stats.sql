-- SQLite does not support CREATE DATABASE and USE commands
-- These are MySQL specific commands and should be removed

-- Create table if not exists
CREATE TABLE IF NOT EXISTS stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node TEXT,
    cpu_usage TEXT,
    cpu_percentage TEXT,
    memory_usage TEXT,
    memory_percentage TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Drop table (if needed to reset the table)
-- Uncomment if you need to clear existing data
-- DROP TABLE IF EXISTS stats;

-- Create table again (ensure this is not redundant)
-- Uncomment if you need to re-create the table
-- CREATE TABLE IF NOT EXISTS stats (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     node TEXT,
--     cpu_usage TEXT,
--     cpu_percentage TEXT,
--     memory_usage TEXT,
--     memory_percentage TEXT,
--     timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
-- );

-- Select data from the table
SELECT * FROM stats;
