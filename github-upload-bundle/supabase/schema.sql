create table if not exists public.slots (
  id bigint generated always as identity primary key,
  slug text not null unique,
  event_date date not null,
  event_time text not null,
  venue text not null,
  area text default '',
  needs text not null,
  status text not null default 'available' check (status in ('available', 'booked')),
  sort_order integer not null default 0,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.registrations (
  id bigint generated always as identity primary key,
  slot_id bigint not null unique references public.slots(id) on delete cascade,
  full_name text not null,
  email text not null,
  company_role text default '',
  attendee_role text not null,
  notes text default '',
  created_at timestamptz not null default timezone('utc', now())
);

create or replace function public.book_slot(
  p_slot_id bigint,
  p_full_name text,
  p_email text,
  p_company_role text default '',
  p_attendee_role text default 'attorney',
  p_notes text default ''
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  slot_row public.slots%rowtype;
  registration_row public.registrations%rowtype;
begin
  select *
  into slot_row
  from public.slots
  where id = p_slot_id
  for update;

  if not found then
    raise exception 'Selected slot was not found.';
  end if;

  if slot_row.status <> 'available' then
    raise exception 'That slot is no longer available.';
  end if;

  insert into public.registrations (
    slot_id,
    full_name,
    email,
    company_role,
    attendee_role,
    notes
  )
  values (
    p_slot_id,
    trim(p_full_name),
    trim(p_email),
    trim(coalesce(p_company_role, '')),
    trim(coalesce(p_attendee_role, 'attorney')),
    trim(coalesce(p_notes, ''))
  )
  returning *
  into registration_row;

  update public.slots
  set status = 'booked'
  where id = p_slot_id;

  return jsonb_build_object(
    'id', registration_row.id,
    'fullName', registration_row.full_name,
    'email', registration_row.email,
    'companyRole', coalesce(registration_row.company_role, ''),
    'attendeeRole', registration_row.attendee_role,
    'notes', coalesce(registration_row.notes, ''),
    'createdAt', registration_row.created_at,
    'slot', jsonb_build_object(
      'id', slot_row.id,
      'slug', slot_row.slug,
      'date', slot_row.event_date,
      'time', slot_row.event_time,
      'venue', slot_row.venue,
      'area', coalesce(slot_row.area, ''),
      'needs', slot_row.needs
    )
  );
end;
$$;

insert into public.slots (slug, event_date, event_time, venue, area, needs, status, sort_order)
values
  ('sarabeths-greenwich-0506', '2026-05-06', '12:30 PM', 'Sarabeth''s Greenwich', 'Greenwich Village', 'Needs attorney & lender', 'available', 1),
  ('green-kitchen-ues-0512', '2026-05-12', '10:30 AM', 'Green Kitchen UES', 'Upper East Side', 'Needs attorney & lender', 'available', 2),
  ('bowery-road-0520', '2026-05-20', '10:30 AM', 'Bowery Road Union Square', 'Union Square', 'Needs attorney & lender', 'available', 3),
  ('cafe-paulette-0522', '2026-05-22', '10:30 AM', 'Café Paulette Fort Greene', 'Fort Greene', 'Needs attorney & lender', 'available', 4),
  ('sarabeths-uws-0526', '2026-05-26', '10:30 AM', 'Sarabeth''s UWS', 'Upper West Side', 'Needs attorney & lender', 'available', 5)
on conflict (slug) do nothing;
