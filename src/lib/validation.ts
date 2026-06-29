import { z } from "zod";

/** Email + password credentials, validated server-side in the auth actions. */
export const credentialsSchema = z.object({
  email: z.string().trim().email("Enter a valid email address"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});
export type Credentials = z.infer<typeof credentialsSchema>;

/** Alert preferences shape (used by the preferences UI). */
export const alertPreferencesSchema = z.object({
  level: z.number().int().min(1).max(5),
  frequency: z.enum(["Instant", "Daily", "Weekly"]),
  email: z.boolean(),
  push: z.boolean(),
  interests: z.array(z.string()),
});
export type AlertPreferences = z.infer<typeof alertPreferencesSchema>;

/** First human-readable issue message from a failed parse. */
export function firstIssue(error: z.ZodError): string {
  return error.issues[0]?.message ?? "Invalid input";
}
