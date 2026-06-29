"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { isSupabaseConfigured } from "@/lib/env";
import { credentialsSchema, firstIssue } from "@/lib/validation";

function safeNext(value: FormDataEntryValue | null): string {
  const next = typeof value === "string" ? value : "";
  // Only allow same-origin absolute paths to avoid open-redirects.
  return next.startsWith("/") && !next.startsWith("//") ? next : "/collection";
}

export async function login(formData: FormData) {
  const next = safeNext(formData.get("next"));

  if (!isSupabaseConfigured()) {
    redirect(`/login?error=${encodeURIComponent("demo")}`);
  }

  const parsed = credentialsSchema.safeParse({
    email: String(formData.get("email") ?? ""),
    password: String(formData.get("password") ?? ""),
  });
  if (!parsed.success) {
    redirect(
      `/login?error=${encodeURIComponent(firstIssue(parsed.error))}&next=${encodeURIComponent(next)}`,
    );
  }

  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword(parsed.data);

  if (error) {
    redirect(`/login?error=${encodeURIComponent(error.message)}`);
  }

  revalidatePath("/", "layout");
  redirect(next);
}

export async function signup(formData: FormData) {
  if (!isSupabaseConfigured()) {
    redirect(`/signup?error=${encodeURIComponent("demo")}`);
  }

  const parsed = credentialsSchema.safeParse({
    email: String(formData.get("email") ?? ""),
    password: String(formData.get("password") ?? ""),
  });
  if (!parsed.success) {
    redirect(`/signup?error=${encodeURIComponent(firstIssue(parsed.error))}`);
  }

  const supabase = await createClient();
  const { data, error } = await supabase.auth.signUp(parsed.data);

  if (error) {
    redirect(`/signup?error=${encodeURIComponent(error.message)}`);
  }

  // If email confirmations are enabled there is no active session yet.
  if (!data.session) {
    redirect(`/login?notice=${encodeURIComponent("check-email")}`);
  }

  revalidatePath("/", "layout");
  redirect("/collection");
}

export async function signout() {
  if (isSupabaseConfigured()) {
    const supabase = await createClient();
    await supabase.auth.signOut();
  }
  revalidatePath("/", "layout");
  redirect("/");
}

export async function toggleSaved(formData: FormData) {
  const propertyId = String(formData.get("propertyId") ?? "");
  const redirectTo = safeNext(formData.get("redirectTo"));

  if (!isSupabaseConfigured() || !propertyId) {
    redirect(`/login?next=${encodeURIComponent(redirectTo)}`);
  }

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect(`/login?next=${encodeURIComponent(redirectTo)}`);
  }

  // Toggle: remove if present, otherwise add.
  const { data: existing } = await supabase
    .from("collections")
    .select("id")
    .eq("user_id", user.id)
    .eq("property_id", propertyId)
    .maybeSingle();

  if (existing) {
    await supabase.from("collections").delete().eq("id", existing.id);
  } else {
    await supabase
      .from("collections")
      .insert({ user_id: user.id, property_id: propertyId });
  }

  revalidatePath("/collection");
  revalidatePath(`/property/${propertyId}`);
  revalidatePath("/");
}
