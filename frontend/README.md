# AI Newsroom — Frontend

Next.js (App Router) · TypeScript · Tailwind CSS v4 · Base UI / shadcn-style components.

## Routes

- Public site: `/`, `/about`, `/latest`, `/search`, `/article/[slug]`, `/category/[slug]`
- Operator dashboard: `/dashboard` and `/dashboard/{stories,research,verification,articles,sources,agents,settings,instagram,publishing}`

Dashboard pages are client components that call the FastAPI backend directly via
`lib/api.ts` (which reads `NEXT_PUBLIC_API_URL`).

## Scripts

```bash
npm run dev     # http://localhost:3000
npm run build   # type-check + production build
npm run lint    # eslint
```

## Environment

Copy `.env.example` to `.env.local` and set `NEXT_PUBLIC_API_URL` to the backend
base URL (default `http://localhost:8000`).

See the repository root `README.md` for the full project, architecture, and
docs in `../docs/`.