-- Self-referential: create the migrations tracking table itself.
-- This runs as part of the bootstrap — the runner creates this table
-- before running any migrations, so this file is a no-op sentinel
-- that marks "migration system initialized" in the tracking table.
SELECT 1;
