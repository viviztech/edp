import "server-only";
import { cache } from "react";
import type { components } from "./api-contracts";
import { publicPages } from "./public-pages";

type PublishedPage = components["schemas"]["PublicPage"];

const navigationOrder = [
  "about",
  "eligibility",
  "benefits",
  "training-structure",
  "mentors",
  "success-stories",
  "resources",
] as const;

const order = new Map<string, number>(navigationOrder.map((slug, index) => [slug, index]));

export const publicNavigation = cache(async (locale: string): Promise<PublishedPage[]> => {
  const response = await publicPages(locale);
  if (!response?.ok) return [];
  const data = (await response.json()) as components["schemas"]["PublicList"];
  return data.items
    .filter((page) => order.has(page.slug))
    .sort((left, right) => order.get(left.slug)! - order.get(right.slug)!);
});
