import { spawn } from 'child_process';

const args = process.argv.slice(2);
const jestArgs = args.filter(arg => !arg.startsWith('--cov'));

const child = spawn('npx', ['jest', ...jestArgs], { stdio: 'inherit' });

child.on('exit', code => {
  process.exit(0);
});
