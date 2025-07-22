import { glob } from 'glob';
import { readFile, writeFile, mkdir } from 'fs/promises';
import path from 'path';
import TOML from 'toml';

// Centralized Heuristics Engine: Define application-specific logic here.
function deriveOperationalLimits(modelId, rawProps) {
  const context = rawProps.limit?.context ?? 4096;
  const output = rawProps.limit?.output ?? 1024;

  // Derive operational values from raw specs
  return {
    id: modelId,
    contextWindow: context,
    limits: {
      chunkSize: Math.floor(context * 0.75), // Use 75% of context for splitting
      summaryMaxTokens: Math.min(output, 4096), // Cap summaries at 4k for quality
      truncateThreshold: context < 8192 ? 1.5 : 1.25, // Heuristic for cheap truncation
    },
  };
}

async function generate() {
  const modelFiles = await glob('providers/**/*.toml');
  const modelProperties = {};

  for (const file of modelFiles) {
    try {
      const modelId = file.replace('providers/', '').replace('.toml', '');
      const content = await readFile(file, 'utf-8');
      const rawProps = TOML.parse(content);
      modelProperties[modelId] = deriveOperationalLimits(modelId, rawProps);
      console.log(`[SUCCESS] Processed: ${modelId}`);
    } catch (error) {
      console.error(`[ERROR] Failed to process ${file}:`, error.message);
    }
  }

  // Add a mandatory default fallback model
  modelProperties['default'] = {
    id: 'default',
    contextWindow: 4096,
    limits: { chunkSize: 3000, summaryMaxTokens: 1024, truncateThreshold: 1.5 },
  };

  const outputPath = path.join('dist', 'model-properties.json');
  await mkdir(path.dirname(outputPath), { recursive: true });
  await writeFile(outputPath, JSON.stringify(modelProperties, null, 2));

  console.log(`
✅ Generated model properties at ${outputPath}`);
}

generate();
