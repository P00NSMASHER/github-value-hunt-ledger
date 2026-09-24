# Production Source of Truth

Phase 1 establishes one authoritative stack:

1. **Canonical code/contracts:** `main:ai_business_os/`
2. **Versioned database definition:** `main:supabase/migrations/ai_business_os/`
3. **Mutable operating state:** private `ai_business_os_prod` database
4. **Legacy implementation:** `business_os/` frozen and non-canonical
5. **Production-bootstrap branch:** historical handoff only until Phase-2 branch cleanup

No branch may define production behavior that lacks a corresponding canonical code or migration
artifact on `main`.
