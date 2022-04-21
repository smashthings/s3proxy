#!/usr/local/lib/nodejs/bin/node

const { build } = require("esbuild");
const { solidPlugin } = require("esbuild-plugin-solid");

build({
  entryPoints: ["templates/app.jsx"],
  bundle: true,
  outfile: "templates/out.js",
  minify: false,
  loader: {
    ".svg": "dataurl",
  },
  logLevel: "info",
  plugins: [solidPlugin()]
}).catch(() => process.exit(1));