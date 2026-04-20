import { useState } from "react";

function toHex(buffer) {
  return Array.from(new Uint8Array(buffer))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

export function useSha256() {
  const [sha256, setSha256] = useState("");
  const [hashing, setHashing] = useState(false);

  const hashFile = async (file) => {
    setHashing(true);
    try {
      const arrayBuffer = await file.arrayBuffer();
      const digest = await crypto.subtle.digest("SHA-256", arrayBuffer);
      const hex = toHex(digest);
      setSha256(hex);
      return hex;
    } finally {
      setHashing(false);
    }
  };

  return { sha256, hashing, hashFile };
}
