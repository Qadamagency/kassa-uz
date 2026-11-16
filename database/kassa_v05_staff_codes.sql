-- KASSA.UZ v0.5 — generate staff codes automatically
-- Apply AFTER database/kassa_v04_schema.sql on a NEW dedicated KASSA.UZ project.
-- No passwords or real accounts are created by this migration.
-- Visible codes are identifiers, NOT authenticators. Login requires verified password/PIN.
-- Prefix + four random digits. Capacity is limited to 9000 codes per prefix/company.
create or replace function public.kassa_staff_code_before_insert()
returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
declare
  prefix text;
  proposed text;
  attempt integer;
begin
  prefix := case new.role
    when 'seller' then 'SV'
    when 'manager' then 'MN'
    when 'director' then 'DR'
    when 'owner' then 'OW'
    else null
  end;
  if prefix is null then raise exception 'Unsupported employee role'; end if;

  -- The server must never accept a user-supplied employee_code during employee creation.
  -- Override any supplied code, so users cannot choose their own visible identifier.
  for attempt in 1..100 loop
    proposed := prefix || '-' || lpad((1000 + (('x' || encode(gen_random_bytes(4),'hex'))::bit(32)::bigint % 9000))::text, 4, '0');
    if not exists (
      select 1 from public.kassa_staff s
      where s.company_id = new.company_id and s.employee_code = proposed
    ) then
      new.employee_code := proposed;
      return new;
    end if;
  end loop;
  raise exception 'Staff code capacity exhausted; switch to a longer random code';
end;
$$;
drop trigger if exists kassa_auto_staff_code on public.kassa_staff;
create trigger kassa_auto_staff_code
before insert on public.kassa_staff
for each row execute function public.kassa_staff_code_before_insert();

-- The uniqueness constraint in v0.4 enforces (company_id, employee_code).
-- Concurrent insert race: unique violation may still occur; retry the full transaction server-side.
-- Do NOT grant INSERT to browser users. Only a trusted backend may create employees,
-- after checking requester identity and (owner|director) role in the same company.
revoke execute on function public.kassa_staff_code_before_insert() from public, anon, authenticated;

-- Employee creation policy for application backend:
-- owner: may create seller / manager / director / owner if business approves
-- director: may create seller / manager; cannot elevate others to director / owner
-- seller / manager: cannot create staff
-- all creation, changes, account blocking must be written to kassa_audit
