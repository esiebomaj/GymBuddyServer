-- ============================================================================
-- GymBuddy: initial schema
-- Tables: user_settings, gym_visits, streaks
-- All FK to auth.users(id). RLS enforced: users access only their own rows.
-- A trigger on auth.users auto-creates default user_settings + streaks rows.
-- ============================================================================

-- 1. user_settings ───────────────────────────────────────────────────────────

create table if not exists public.user_settings (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references auth.users(id) on delete cascade,
    weekly_goal smallint not null default 3 check (weekly_goal between 1 and 7),
    gym_days    smallint[] not null default '{1,2,3,4,5}',
    lock_start_time time not null default '06:00',
    lock_end_time   time not null default '22:00',
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now(),
    constraint user_settings_user_id_unique unique (user_id)
);

alter table public.user_settings enable row level security;

create policy "Users can read own settings"
    on public.user_settings for select
    using (auth.uid() = user_id);

create policy "Users can update own settings"
    on public.user_settings for update
    using (auth.uid() = user_id);

create policy "Service role can insert settings"
    on public.user_settings for insert
    with check (true);

-- 2. gym_visits ──────────────────────────────────────────────────────────────

create table if not exists public.gym_visits (
    id           uuid primary key default gen_random_uuid(),
    user_id      uuid not null references auth.users(id) on delete cascade,
    visit_date   date not null,
    workout_type text not null,
    note         text check (char_length(note) <= 280),
    photo_url    text,
    created_at   timestamptz not null default now(),
    constraint gym_visits_one_per_day unique (user_id, visit_date)
);

alter table public.gym_visits enable row level security;

create policy "Users can read own visits"
    on public.gym_visits for select
    using (auth.uid() = user_id);

create policy "Users can insert own visits"
    on public.gym_visits for insert
    with check (auth.uid() = user_id);

-- 3. streaks ─────────────────────────────────────────────────────────────────

create table if not exists public.streaks (
    id                  uuid primary key default gen_random_uuid(),
    user_id             uuid not null references auth.users(id) on delete cascade,
    current_streak      int not null default 0,
    longest_streak      int not null default 0,
    last_completed_week date,
    updated_at          timestamptz not null default now(),
    constraint streaks_user_id_unique unique (user_id)
);

alter table public.streaks enable row level security;

create policy "Users can read own streaks"
    on public.streaks for select
    using (auth.uid() = user_id);

create policy "Users can update own streaks"
    on public.streaks for update
    using (auth.uid() = user_id);

create policy "Service role can insert streaks"
    on public.streaks for insert
    with check (true);

-- 4. Trigger: auto-create rows on sign-up ────────────────────────────────────

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = ''
as $$
begin
    insert into public.user_settings (user_id) values (new.id);
    insert into public.streaks (user_id) values (new.id);
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- 5. Supabase Storage bucket for proof photos ────────────────────────────────

insert into storage.buckets (id, name, public)
values ('proof-photos', 'proof-photos', true)
on conflict (id) do nothing;

create policy "Users can upload proof photos"
    on storage.objects for insert
    with check (
        bucket_id = 'proof-photos'
        and auth.role() = 'authenticated'
    );

create policy "Anyone can read proof photos"
    on storage.objects for select
    using (bucket_id = 'proof-photos');


ALTER TABLE public.user_settings ADD COLUMN free_updates_remaining int NOT NULL DEFAULT 2;