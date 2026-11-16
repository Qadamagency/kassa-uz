-- KASSA.UZ v0.4 — role-based multi-branch schema (PostgreSQL/Supabase)
-- This is a migration blueprint; DO NOT run in an existing unrelated project.
create extension if not exists pgcrypto;
create table if not exists public.kassa_companies (
 id uuid primary key default gen_random_uuid(),
 name text not null,
 created_at timestamptz not null default now()
);
create table if not exists public.kassa_branches (
 id uuid primary key default gen_random_uuid(),
 company_id uuid not null references public.kassa_companies(id),
 name text not null,
 created_at timestamptz not null default now(),
 unique(id,company_id)
);
create table if not exists public.kassa_staff (
 id uuid primary key default gen_random_uuid(),
 company_id uuid not null references public.kassa_companies(id),
 branch_id uuid,
 auth_user_id uuid unique references auth.users(id) on delete set null,
 employee_code text not null,
 display_name text not null,
 role text not null check (role in ('seller','manager','director','owner')),
 active boolean not null default true,
 created_at timestamptz not null default now(),
 unique(company_id,employee_code),
 foreign key(branch_id,company_id) references public.kassa_branches(id,company_id),
 check(role in ('director','owner') or branch_id is not null),
 check(employee_code ~ '^(SV|MN|DR|OW)-[0-9]{4,8}$')
);
create table if not exists public.kassa_products (
 id uuid primary key default gen_random_uuid(),
 company_id uuid not null references public.kassa_companies(id),
 name text not null,
 sku text,
 barcode text not null,
 price_som bigint not null check(price_som>=0),
 cost_som bigint not null default 0 check(cost_som>=0),
 active boolean not null default true,
 created_by uuid references public.kassa_staff(id),
 created_at timestamptz not null default now(),
 unique(company_id,barcode),
 unique(id,company_id)
);
create unique index if not exists kassa_products_sku_unique on public.kassa_products(company_id,sku) where sku is not null;
create table if not exists public.kassa_stock (
 company_id uuid not null references public.kassa_companies(id),
 branch_id uuid not null,
 product_id uuid not null,
 quantity bigint not null default 0 check(quantity>=0),
 updated_at timestamptz not null default now(),
 primary key(branch_id,product_id),
 foreign key(branch_id,company_id) references public.kassa_branches(id,company_id),
 foreign key(product_id,company_id) references public.kassa_products(id,company_id)
);
create table if not exists public.kassa_sales (
 id uuid primary key default gen_random_uuid(),
 company_id uuid not null references public.kassa_companies(id),
 branch_id uuid not null,
 seller_id uuid not null references public.kassa_staff(id),
 total_som bigint not null check(total_som>=0),
 payment_kind text not null check(payment_kind in ('cash','card_recorded','split')),
 request_key uuid not null,
 created_at timestamptz not null default now(),
 unique(company_id,request_key),
 unique(id,company_id),
 foreign key(branch_id,company_id) references public.kassa_branches(id,company_id)
);
create table if not exists public.kassa_sale_items (
 id uuid primary key default gen_random_uuid(),
 company_id uuid not null references public.kassa_companies(id),
 sale_id uuid not null,
 product_id uuid not null,
 barcode_snapshot text not null,
 name_snapshot text not null,
 quantity bigint not null check(quantity>0),
 unit_price_som bigint not null check(unit_price_som>=0),
 cost_snapshot_som bigint not null check(cost_snapshot_som>=0),
 foreign key(sale_id,company_id) references public.kassa_sales(id,company_id),
 foreign key(product_id,company_id) references public.kassa_products(id,company_id)
);
create table if not exists public.kassa_stock_movements (
 id uuid primary key default gen_random_uuid(),
 company_id uuid not null references public.kassa_companies(id),
 branch_id uuid not null,
 product_id uuid not null,
 actor_id uuid not null references public.kassa_staff(id),
 delta bigint not null check(delta<>0),
 reason text not null check(reason in ('receipt','sale','return','adjustment','transfer_in','transfer_out')),
 source_id uuid,
 created_at timestamptz not null default now(),
 foreign key(branch_id,company_id) references public.kassa_branches(id,company_id),
 foreign key(product_id,company_id) references public.kassa_products(id,company_id)
);
create table if not exists public.kassa_audit (
 id bigint generated always as identity primary key,
 company_id uuid not null references public.kassa_companies(id),
 actor_id uuid references public.kassa_staff(id),
 action text not null,
 entity_type text not null,
 entity_id uuid,
 details jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now()
);
create index if not exists kassa_sales_seller_time on public.kassa_sales(seller_id,created_at desc);
create index if not exists kassa_sales_branch_time on public.kassa_sales(branch_id,created_at desc);
create index if not exists kassa_movement_product_time on public.kassa_stock_movements(product_id,created_at desc);
-- SAFETY: default deny for all browser clients until fully tested RLS policies and atomic sale RPC are implemented.
alter table public.kassa_companies enable row level security;
alter table public.kassa_branches enable row level security;
alter table public.kassa_staff enable row level security;
alter table public.kassa_products enable row level security;
alter table public.kassa_stock enable row level security;
alter table public.kassa_sales enable row level security;
alter table public.kassa_sale_items enable row level security;
alter table public.kassa_stock_movements enable row level security;
alter table public.kassa_audit enable row level security;
revoke all on public.kassa_companies,public.kassa_branches,public.kassa_staff,public.kassa_products,public.kassa_stock,public.kassa_sales,public.kassa_sale_items,public.kassa_stock_movements,public.kassa_audit from anon,authenticated;
-- No automatic demo accounts. Never store PINs in plain text or expose Supabase service keys in GitHub Pages.
