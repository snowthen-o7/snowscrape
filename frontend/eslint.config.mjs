// Flat ESLint config (ESLint 9 + Next.js 16). Replaces the legacy .eslintrc.json
// and the removed `next lint` command. Mirrors the project's prior ruleset, which
// extended only `next/typescript`.
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
    // Soften two rules without hard-failing CI:
    //  - no-explicit-any: pervasive, pre-existing in the API/websocket payload
    //    layer; keep it visible as a warning and ratchet it down separately.
    //  - no-require-imports: only hit by config files / the .cjs git-auth
    //    script, where require() is the correct idiom.
    plugins: { '@typescript-eslint': tsPlugin },
    rules: {
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-require-imports': 'off',
    },
  },
];

export default eslintConfig;
