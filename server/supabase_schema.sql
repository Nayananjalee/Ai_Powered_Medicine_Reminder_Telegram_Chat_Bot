-- Users table
create table if not exists users (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    phone text unique not null,
    telegram_id text
);

-- Medications table
create table if not exists medications (
    id uuid primary key default gen_random_uuid(),
    user_phone text references users(phone) on delete cascade,
    name text not null,
    quantity integer not null,
    meal_timing text not null check (meal_timing in ('before', 'after')),
    frequency text not null check (frequency in ('daily', 'every6hours')),
    time text not null, -- 'HH:MM' format
    sent boolean default false
);