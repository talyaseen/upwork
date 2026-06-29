"use client";

import { useFormStatus } from "react-dom";

interface Props {
  children: React.ReactNode;
  pendingLabel?: React.ReactNode;
  className?: string;
  disabled?: boolean;
}

/**
 * Submit button wired to the enclosing <form>'s pending state. Must be rendered
 * inside a <form> that uses a Server Action.
 */
export function SubmitButton({
  children,
  pendingLabel,
  className = "",
  disabled = false,
}: Props) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending || disabled}
      aria-busy={pending}
      className={`disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
    >
      {pending ? (pendingLabel ?? children) : children}
    </button>
  );
}
