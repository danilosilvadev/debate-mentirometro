// Supabase Edge Function: POST /functions/v1/livepix-webhook  (deploy com --no-verify-jwt; a LivePix não manda JWT)
// Segredos (supabase secrets set): LIVEPIX_CLIENT_ID, LIVEPIX_CLIENT_SECRET, GROQ_API_KEY, PLACAR_DEBATE_KEY.
import { createClient } from 'npm:@supabase/supabase-js@2'
import { handle } from './core.mjs'

const env = Deno.env.toObject()
const db = createClient(env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY)

Deno.serve(async (req) => {
  if (req.method !== 'POST') return new Response('método', { status: 405 })
  let payload: unknown
  try { payload = await req.json() } catch { return new Response('json', { status: 400 }) }
  const out = await (handle as any)(payload, env, {
    fetch,
    debate: env.PLACAR_DEBATE_KEY || 'ao-vivo',
    insert: async (row: Record<string, unknown>) => {
      const { error } = await db.from('superchats').upsert(row, { onConflict: 'livepix_id', ignoreDuplicates: true })
      if (error) throw new Error(error.message)
    },
  })
  return Response.json(out.body, { status: out.status })
})
