begin;

create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default 'Candidate' check (char_length(display_name) between 1 and 80),
  avatar_url text,
  timezone text not null default 'Asia/Kolkata',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.mock_attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  slug text not null,
  title text not null,
  attempted_at timestamptz,
  imported_at timestamptz not null default timezone('utc', now()),
  payload jsonb not null check (jsonb_typeof(payload) = 'object'),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (user_id, slug)
);

create table if not exists public.question_reviews (
  user_id uuid not null references auth.users(id) on delete cascade,
  mock_slug text not null,
  question_id text not null,
  status text not null check (status in ('again', 'learning', 'mastered')),
  note text not null default '' check (char_length(note) <= 2000),
  review_count integer not null default 1 check (review_count > 0),
  last_reviewed_at timestamptz not null default timezone('utc', now()),
  next_review_at timestamptz not null,
  interval_days integer not null check (interval_days in (1, 3, 14)),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  primary key (user_id, mock_slug, question_id),
  foreign key (user_id, mock_slug) references public.mock_attempts(user_id, slug) on delete cascade
);

create index if not exists mock_attempts_user_imported_idx
  on public.mock_attempts(user_id, imported_at desc);
create index if not exists question_reviews_user_due_idx
  on public.question_reviews(user_id, next_review_at);

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at before update on public.profiles
for each row execute function public.set_updated_at();

drop trigger if exists mock_attempts_set_updated_at on public.mock_attempts;
create trigger mock_attempts_set_updated_at before update on public.mock_attempts
for each row execute function public.set_updated_at();

drop trigger if exists question_reviews_set_updated_at on public.question_reviews;
create trigger question_reviews_set_updated_at before update on public.question_reviews
for each row execute function public.set_updated_at();

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, display_name, avatar_url)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'full_name', split_part(coalesce(new.email, 'Candidate'), '@', 1)),
    new.raw_user_meta_data ->> 'avatar_url'
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();

alter table public.profiles enable row level security;
alter table public.mock_attempts enable row level security;
alter table public.question_reviews enable row level security;

drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own" on public.profiles
for select to authenticated using ((select auth.uid()) = id);
drop policy if exists "profiles_insert_own" on public.profiles;
create policy "profiles_insert_own" on public.profiles
for insert to authenticated with check ((select auth.uid()) = id);
drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own" on public.profiles
for update to authenticated using ((select auth.uid()) = id) with check ((select auth.uid()) = id);

drop policy if exists "mocks_select_own" on public.mock_attempts;
create policy "mocks_select_own" on public.mock_attempts
for select to authenticated using ((select auth.uid()) = user_id);
drop policy if exists "mocks_insert_own" on public.mock_attempts;
create policy "mocks_insert_own" on public.mock_attempts
for insert to authenticated with check ((select auth.uid()) = user_id);
drop policy if exists "mocks_update_own" on public.mock_attempts;
create policy "mocks_update_own" on public.mock_attempts
for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
drop policy if exists "mocks_delete_own" on public.mock_attempts;
create policy "mocks_delete_own" on public.mock_attempts
for delete to authenticated using ((select auth.uid()) = user_id);

drop policy if exists "reviews_select_own" on public.question_reviews;
create policy "reviews_select_own" on public.question_reviews
for select to authenticated using ((select auth.uid()) = user_id);
drop policy if exists "reviews_insert_own" on public.question_reviews;
create policy "reviews_insert_own" on public.question_reviews
for insert to authenticated with check ((select auth.uid()) = user_id);
drop policy if exists "reviews_update_own" on public.question_reviews;
create policy "reviews_update_own" on public.question_reviews
for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
drop policy if exists "reviews_delete_own" on public.question_reviews;
create policy "reviews_delete_own" on public.question_reviews
for delete to authenticated using ((select auth.uid()) = user_id);

revoke all on public.profiles, public.mock_attempts, public.question_reviews from anon;
grant select, insert, update, delete on public.profiles, public.mock_attempts, public.question_reviews to authenticated;

create or replace function public.cat_portal_health()
returns jsonb
language sql
stable
security invoker
set search_path = ''
as $$
  select jsonb_build_object(
    'status', 'ready',
    'schema_version', '20260904000000',
    'rls', true
  );
$$;

revoke all on function public.cat_portal_health() from public;
grant execute on function public.cat_portal_health() to anon, authenticated;

commit;