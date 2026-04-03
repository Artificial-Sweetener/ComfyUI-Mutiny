import { readFileSync, writeFileSync } from "node:fs";

const nextVersion = process.argv[2];

if (!nextVersion) {
    throw new Error("Expected the next release version as the first argument.");
}

function replaceVersionField(filePath, pattern, replacement) {
    const originalText = readFileSync(filePath, "utf8");
    const updatedText = originalText.replace(pattern, replacement);

    if (updatedText === originalText) {
        throw new Error(`Could not find a version field in ${filePath.pathname}.`);
    }

    writeFileSync(filePath, updatedText, "utf8");
}

replaceVersionField(
    new URL("../package.json", import.meta.url),
    /^  "version": "[^"]+",$/m,
    `  "version": "${nextVersion}",`,
);

replaceVersionField(
    new URL("../pyproject.toml", import.meta.url),
    /^version = "[^"]+"$/m,
    `version = "${nextVersion}"`,
);
