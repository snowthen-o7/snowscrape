// Flat ESLint config (ESLint 9 + Next.js 16). Replaces the legacy .eslintrc.json
// and the removed `next lint` command. Based on the project's prior ruleset
// (which extended only `next/typescript`), with two rules softened (see below).
import nextTypescript from 'eslint-config-next/typescript';

// Reuse the exact @typescript-eslint plugin instance the preset registers.
// (pnpm can resolve a second physical copy of typescript-eslint, so importing it
// directly would trip ESLint's "Cannot redefine plugin" guard.)
const tsPlugin = nextTypescript.find(
  (c) => c.plugins && c.plugins['@typescript-eslint'],
)?.plugins['@typescript-eslint'];

const eslintConfig = [
  {
    ignores: [
      '.next/**',
      'node_modules/**',
      'coverage/**',
      'playwright-report/**',
      'test-results/**',
      'next-env.d.ts',
      'sst-env.d.ts',
    ],
  },
  ...nextTypescript,
  {
    // no-explicit-any is pervasive and pre-existing in the API/websocket payload
    // layer; keep it visible as a warning and ratchet it down separately rather
    // than hard-failing CI. (Reuse the preset's plugin instance; see above.)
    plugins: { '@typescript-eslint': tsPlugin },
    rules: {
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
  {
    // Config files and the CommonJS git-auth script legitimately use require();
    // keep the rule as an error everywhere else.
    files: ['**/*.config.{js,cjs,mjs,ts}', '**/*.cjs'],
    plugins: { '@typescript-eslint': tsPlugin },
    rules: {
      '@typescript-eslint/no-require-imports': 'off',
    },
  },
];

export default eslintConfig;
