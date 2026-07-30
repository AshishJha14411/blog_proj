/**
 * Typed API surface generated from the backend's OpenAPI schema.
 *
 * WHY: hand-written frontend types drift from the backend and the compiler
 * can't catch it — that's the exact bug class that bit us (PostOut vs Post,
 * the `status` union that failed the build, UUIDs typed as numbers). These
 * aliases come straight from `lib/api-types.ts`, which is regenerated from
 * `/openapi.json` via `npm run gen:api`. If the backend schema changes and
 * the frontend isn't regenerated, the types stop compiling — drift becomes a
 * build error instead of a runtime surprise.
 *
 * Regenerate:  npm run gen:api   (backend must be running on :8000)
 */
import type { components } from "./api-types";

type Schemas = components["schemas"];

// Stories
export type StoryOut = Schemas["StoryOut"];
export type StoryList = Schemas["StoryList"];
export type StoryCreate = Schemas["StoryCreate"];
export type StoryUpdate = Schemas["StoryUpdate"];
export type StoryGenerateIn = Schemas["StoryGenerateIn"];
export type UserSummary = Schemas["UserSummary"];

// Auth / users
export type UserProfile = Schemas["UserProfile"];
export type LoginResponse = Schemas["LoginResponse"];

// Webhooks
export type WebhookOut = Schemas["WebhookOut"];
export type WebhookCreated = Schemas["WebhookCreated"];

// Analytics
export type DayCount = Schemas["DayCount"];

// Admin
export type CreatorRequestOut = Schemas["CreatorRequestOut"];
