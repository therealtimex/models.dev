import { glob } from 'glob';
import { readFile, writeFile, mkdir } from 'fs/promises';
import path from 'path';
import TOML from 'toml';

async function generate() {
  const providerDirs = await glob('providers/*', { mark: true });
  const finalOutput = {};

  for (const dir of providerDirs) {
    if (!dir.endsWith('/')) continue; // Skip files, process only directories

    const providerTomlPath = path.join(dir, 'provider.toml');
    const providerId = dir.replace('providers/', '').replace('/', '');

    try {
      const providerContent = await readFile(providerTomlPath, 'utf-8');
      const providerProps = TOML.parse(providerContent);

      const providerData = {
        id: providerId,
        name: providerProps.name || providerId,
        models: {},
      };

      const modelFiles = await glob(path.join(dir, 'models/**/*.toml'));

      for (const modelFile of modelFiles) {
        const modelId = path.basename(modelFile, '.toml');
        const modelContent = await readFile(modelFile, 'utf-8');
        const modelProps = TOML.parse(modelContent);

        providerData.models[modelId] = {
          id: modelId,
          name: modelProps.name || modelId,
          limit: {
            context: modelProps.limit?.context ?? null,
            output: modelProps.limit?.output ?? null,
          },
        };
      }

      finalOutput[providerId] = providerData;
      console.log(`[SUCCESS] Processed provider: ${providerId}`);

    } catch (error) {
      if (error.code !== 'ENOENT') { // Ignore missing provider.toml for now
        console.error(`[ERROR] Failed to process provider ${providerId}:`, error.message);
      } else {
        console.warn(`[WARN] Skipping provider ${providerId}: provider.toml not found.`);
      }
    }
  }

  const outputPath = path.join('dist', 'model-properties.json');
  await mkdir(path.dirname(outputPath), { recursive: true });
  await writeFile(outputPath, JSON.stringify(finalOutput, null, 2));

  console.log(`\n✅ Generated model properties at ${outputPath}`);
}

generate();