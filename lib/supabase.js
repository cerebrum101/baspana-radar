import { createClient } from "@supabase/supabase-js";

// Read-only public client. Uses the anon key; RLS (schema.sql) allows
// SELECT for everyone and blocks writes without the service key.
export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
);
