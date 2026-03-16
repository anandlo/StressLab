"use client";

import Avatar from "boring-avatars";

// A professional set of colors that renders well on both light and dark themes
const PALETTE = ["#3B82F6", "#8B5CF6", "#EC4899", "#0EA5E9", "#10B981"];

interface UserAvatarProps {
  /** Seed for deterministic generation — typically email or display_name */
  name: string;
  size?: number;
}

export function UserAvatar({ name, size = 36 }: UserAvatarProps) {
  return (
    <Avatar
      size={size}
      name={name}
      variant="beam"
      colors={PALETTE}
    />
  );
}
