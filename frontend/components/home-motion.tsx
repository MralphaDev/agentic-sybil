
"use client";

import {
  motion,
  useReducedMotion,
} from "framer-motion";
import type { ReactNode } from "react";
import {
  heroContainer,
  heroItem,
  sectionReveal,
  cardReveal,
} from "../app/animations";

export function HeroMotion({ children }: { children: ReactNode }) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      variants={heroContainer}
      initial="hidden"
      animate="visible"
      transition={reduceMotion ? { duration: 0 } : undefined}
      className="contents"
    >
      {children}
    </motion.div>
  );
}

export function HeroItem({ children }: { children: ReactNode }) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      variants={heroItem}
      initial="hidden"
      animate="visible"
      transition={reduceMotion ? { duration: 0 } : undefined}
    >
      {children}
    </motion.div>
  );
}

export function RevealSection({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      variants={sectionReveal}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.2 }}
      transition={reduceMotion ? { duration: 0 } : undefined}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function FeatureMotion({
  children,
  index,
}: {
  children: ReactNode;
  index: number;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      variants={cardReveal}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.25 }}
      transition={
        reduceMotion
          ? { duration: 0 }
          : { delay: index * 0.14 }
      }
      whileHover={
        reduceMotion
          ? undefined
          : {
              y: -8,
              scale: 1.015,
              transition: { duration: 0.25 },
            }
      }
      className="h-full"
    >
      {children}
    </motion.div>
  );
}

export function CinematicGlow() {
  const reduceMotion = useReducedMotion();

  return (
    <>
      <motion.div
        className="pointer-events-none absolute -right-20 top-1/4 h-96 w-96 rounded-full bg-red-600/15 blur-[120px]"
        animate={
          reduceMotion
            ? undefined
            : {
                x: [0, -50, 20, 0],
                y: [0, 35, -25, 0],
                scale: [1, 1.2, 0.9, 1],
              }
        }
        transition={{
          duration: 16,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />

      <motion.div
        className="pointer-events-none absolute -left-24 bottom-0 h-80 w-80 rounded-full bg-orange-600/10 blur-[110px]"
        animate={
          reduceMotion
            ? undefined
            : {
                x: [0, 45, -20, 0],
                y: [0, -35, 20, 0],
              }
        }
        transition={{
          duration: 13,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
    </>
  );
}
