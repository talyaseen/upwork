"use client";

import { motion, MotionConfig } from "framer-motion";

/**
 * Wraps every route so navigation fades + rises in. `template.tsx` re-mounts on
 * each navigation (unlike layout.tsx), which is what makes the transition run.
 * MotionConfig honours the user's "reduce motion" OS setting app-wide.
 */
export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <MotionConfig reducedMotion="user">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      >
        {children}
      </motion.div>
    </MotionConfig>
  );
}
