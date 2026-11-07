/* Runtime-only TypeScript emit for the private pilot. Keeps the pinned Nest source intact. */
const fs = require("node:fs");
const path = require("node:path");
const project = path.resolve(process.argv[2]);
const ts = require(path.join(project, "node_modules/typescript"));
const destination = path.join(project, "apps/backend/dist");
const config = { target: ts.ScriptTarget.ES2021, module: ts.ModuleKind.CommonJS,
  esModuleInterop: true, experimentalDecorators: true, emitDecoratorMetadata: true };
let count = 0;

function compileDirectory(directory) {
  for (const file of fs.readdirSync(path.join(project, directory), {withFileTypes: true})) {
    const relative = path.join(directory, file.name);
    if (file.isDirectory()) {
      if (!["node_modules", "dist", "__tests__"].includes(file.name)) compileDirectory(relative);
      continue;
    }
    if (!file.isFile() || /\.(?:spec|test|d)\.ts$/.test(file.name) ||
        !/\.(?:ts|js|cjs|json|yaml|prisma|sql)$/.test(file.name)) continue;
    const input = path.join(project, relative);
    const output = path.join(destination, relative.replace(/\.ts$/, ".js"));
    fs.mkdirSync(path.dirname(output), {recursive: true});
    if (file.name.endsWith(".ts")) {
      const source = fs.readFileSync(input, "utf8");
      const result = ts.transpileModule(source, {fileName: input, compilerOptions: config, reportDiagnostics: true});
      if (result.diagnostics.some(d => d.category === ts.DiagnosticCategory.Error))
        throw new Error("TypeScript emit failed: " + relative);
      fs.writeFileSync(output, result.outputText);
      count++;
    } else {
      fs.copyFileSync(input, output);
    }
  }
}
for (const directory of ["apps/backend/src", "libraries"]) compileDirectory(directory);
console.log("Pinned TypeScript modules emitted:", count);
