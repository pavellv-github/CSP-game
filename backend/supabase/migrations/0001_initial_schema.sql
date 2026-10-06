-- Pixel Fantasy Survival — initial schema (Phase 5/6, not used by the MVP client yet).
-- Content tables mirror game/data/*.json: stable text IDs, draft/published/archived status,
-- and the full definition in `data` (same shape as the JSON entry), so the admin panel can edit
-- any field without schema migrations. The client reads only published content.

create type content_status as enum ('draft', 'published', 'archived');

-- Monotonic content version; the client compares it with its cached version on start.
create table content_versions (
  version      integer primary key,
  published_at timestamptz not null default now(),
  notes        text
);

-- Shared columns for every content table.
create or replace function touch_updated_at() returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

do $$
declare
  t text;
begin
  foreach t in array array['characters', 'levels', 'enemies', 'items', 'skills', 'skill_nodes',
                           'upgrades', 'buildings', 'loot_tables', 'xp_curve']
  loop
    execute format($f$
      create table %1$I (
        id              text primary key,          -- never changes after publication
        status          content_status not null default 'draft',
        content_version integer references content_versions(version),
        data            jsonb not null,            -- the definition, same shape as game/data/*.json
        created_at      timestamptz not null default now(),
        updated_at      timestamptz not null default now(),
        constraint %1$s_data_id check (data->>'id' = id)
      );
      create index %1$s_status_idx on %1$I (status);
      create trigger %1$s_touch before update on %1$I for each row execute function touch_updated_at();
      alter table %1$I enable row level security;
      create policy %1$s_read_published on %1$I for select using (status = 'published');
    $f$, t);
  end loop;
end $$;

-- Remote config: versions, feature flags, balance multipliers (key -> jsonb value).
create table game_config (
  key        text primary key,
  value      jsonb not null,
  updated_at timestamptz not null default now()
);
alter table game_config enable row level security;
create policy game_config_read on game_config for select using (true);

-- Player data. One profile per auth user; every row is owned by auth.uid().
create table player_profiles (
  user_id               uuid primary key references auth.users(id) on delete cascade,
  gold                  integer not null default 0 check (gold >= 0),
  selected_character_id text references characters(id),
  total_kills           integer not null default 0,
  runs_played           integer not null default 0,
  save_version          integer not null default 1,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now()
);

create table player_characters (
  user_id      uuid references auth.users(id) on delete cascade,
  character_id text references characters(id),
  unlocked_at  timestamptz not null default now(),
  primary key (user_id, character_id)
);

create table player_inventory (
  id       bigint generated always as identity primary key,
  user_id  uuid not null references auth.users(id) on delete cascade,
  item_id  text not null references items(id),
  quantity integer not null check (quantity > 0),
  equipped boolean not null default false
);
create index player_inventory_user_idx on player_inventory (user_id);

create table player_progress (
  user_id     uuid references auth.users(id) on delete cascade,
  level_id    text references levels(id),
  completions integer not null default 0,
  best_time   real,
  primary key (user_id, level_id)
);

create table player_upgrades (
  user_id    uuid references auth.users(id) on delete cascade,
  upgrade_id text references upgrades(id),
  level      integer not null check (level >= 0),
  primary key (user_id, upgrade_id)
);

create table player_buildings (
  id          bigint generated always as identity primary key,
  user_id     uuid not null references auth.users(id) on delete cascade,
  building_id text not null references buildings(id),
  position    jsonb,
  level       integer not null default 1
);

-- Clients may read their own data. Writes go through Edge Functions (service role),
-- which validate them server-side: the client never performs privileged operations.
do $$
declare
  t text;
begin
  foreach t in array array['player_profiles', 'player_characters', 'player_inventory',
                           'player_progress', 'player_upgrades', 'player_buildings']
  loop
    execute format('alter table %1$I enable row level security;', t);
    execute format('create policy %1$s_owner_read on %1$I for select using (auth.uid() = user_id);', t);
  end loop;
end $$;
