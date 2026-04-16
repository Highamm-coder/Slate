/**
 * /api/fetch-slate — CORS proxy for loading slates from external URLs.
 *
 * The viewer can't fetch() from Google Drive (or most external hosts)
 * directly because they don't include CORS headers. This edge function
 * fetches the URL server-side and returns the HTML body.
 *
 * Usage:
 *   GET /api/fetch-slate?url=https://drive.google.com/uc?export=download&id=ABC
 *
 * Returns the raw HTML with Content-Type: text/html and permissive CORS headers.
 */

export const config = { runtime: 'edge' };

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

// Google Drive URL patterns → direct download URL
function transformDriveURL(url: string): string {
  // Pattern 1: drive.google.com/file/d/ID/view...
  let m = url.match(/drive\.google\.com\/file\/d\/([a-zA-Z0-9_-]+)/);
  if (m) return `https://drive.google.com/uc?export=download&id=${m[1]}`;

  // Pattern 2: drive.google.com/open?id=ID
  m = url.match(/drive\.google\.com\/open\?id=([a-zA-Z0-9_-]+)/);
  if (m) return `https://drive.google.com/uc?export=download&id=${m[1]}`;

  // Pattern 3: docs.google.com/document/d/ID/...
  m = url.match(/docs\.google\.com\/document\/d\/([a-zA-Z0-9_-]+)/);
  if (m) return `https://docs.google.com/document/d/${m[1]}/export?format=html`;

  // Already a direct URL — pass through
  return url;
}

export default async function handler(req: Request): Promise<Response> {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: CORS_HEADERS });
  }

  const { searchParams } = new URL(req.url);
  const rawURL = searchParams.get('url');

  if (!rawURL) {
    return new Response(JSON.stringify({ error: 'Missing ?url= parameter' }), {
      status: 400,
      headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
    });
  }

  // Basic validation — block localhost / internal IPs
  try {
    const parsed = new URL(rawURL);
    const host = parsed.hostname.toLowerCase();
    if (
      host === 'localhost' ||
      host === '127.0.0.1' ||
      host.startsWith('192.168.') ||
      host.startsWith('10.') ||
      host.endsWith('.local')
    ) {
      return new Response(JSON.stringify({ error: 'Internal URLs are not allowed' }), {
        status: 403,
        headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
      });
    }
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid URL' }), {
      status: 400,
      headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
    });
  }

  const fetchURL = transformDriveURL(rawURL);

  try {
    const res = await fetch(fetchURL, {
      headers: { 'User-Agent': 'Slate/1.0 (deck viewer proxy)' },
      redirect: 'follow',
    });

    if (!res.ok) {
      return new Response(
        JSON.stringify({ error: `Upstream returned ${res.status}` }),
        { status: 502, headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' } },
      );
    }

    const body = await res.text();

    return new Response(body, {
      status: 200,
      headers: {
        ...CORS_HEADERS,
        'Content-Type': 'text/html; charset=utf-8',
        'Cache-Control': 'public, max-age=60, s-maxage=300',
      },
    });
  } catch (err: any) {
    return new Response(
      JSON.stringify({ error: err?.message || 'Fetch failed' }),
      { status: 502, headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' } },
    );
  }
}
