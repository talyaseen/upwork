import { toggleSaved } from "@/app/auth/actions";
import { SubmitButton } from "@/components/SubmitButton";

interface Props {
  propertyId: string;
  saved: boolean;
  redirectTo: string;
  variant?: "full" | "icon";
}

/**
 * Save / unsave a property to the signed-in user's collection via a Server
 * Action. When signed-out (or in demo mode) the action redirects to /login.
 */
export function SaveButton({
  propertyId,
  saved,
  redirectTo,
  variant = "full",
}: Props) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-full border text-sm font-medium transition active:scale-[0.98]";
  const tone = saved
    ? "border-gilt/40 bg-gilt/10 text-gilt-soft hover:bg-gilt/15"
    : "border-white/15 bg-white/[0.03] text-white/75 hover:border-white/30 hover:text-white";
  const size =
    variant === "icon" ? "h-10 w-10 text-base" : "w-full px-4 py-2.5";

  return (
    <form action={toggleSaved} className={variant === "full" ? "w-full" : ""}>
      <input type="hidden" name="propertyId" value={propertyId} />
      <input type="hidden" name="redirectTo" value={redirectTo} />
      <SubmitButton className={`${base} ${tone} ${size}`}>
        <span aria-hidden="true" className={saved ? "text-gilt" : ""}>
          {saved ? "♥" : "♡"}
        </span>
        {variant === "full" && <span>{saved ? "Saved" : "Save"}</span>}
      </SubmitButton>
    </form>
  );
}
