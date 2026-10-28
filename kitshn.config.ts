import { defineApp } from "kitshn";

// kitshn 2 (https://kit.yarden-zamir.com): the built site in site/public, public, on both hosts (K-817).
// news.yarden-zamir.com is the canonical host; the-riffle.yarden-zamir.com serves the same files.
export default defineApp({
  static: { output: "site/public" },
  deploy: [
    {
      on: "push",
      branch: "main",
      name: "prod",
      address: ["news.yarden-zamir.com", "the-riffle.yarden-zamir.com"],
      startsIn: "Everyone",
    },
    { on: "pull_request", name: "pr-{pr}", ephemeral: true },
  ],
});
