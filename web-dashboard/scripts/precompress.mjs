// Build-time work only: eight compression jobs, no runtime dependency.
import { readdir, readFile, writeFile, stat, utimes } from 'node:fs/promises'
import { join } from 'node:path'
import { gzip as gzipCallback } from 'node:zlib'
import { promisify } from 'node:util'
const gzip=promisify(gzipCallback), root=process.argv[2]??'out', files=[]
async function walk(dir){for(const e of await readdir(dir,{withFileTypes:true})){const p=join(dir,e.name);if(e.isDirectory())await walk(p);else if(/\.(?:html|js|css|json|svg|txt|xml)$/.test(p)&&(await stat(p)).size>=512)files.push(p)}}
await walk(root)
let next=0
await Promise.all(Array.from({length:8},async()=>{while(next<files.length){const p=files[next++],s=await stat(p),raw=await readFile(p),compressed=await gzip(raw,{level:9});if(compressed.length<raw.length){await writeFile(p+'.gz',compressed);await utimes(p+'.gz',s.atime,s.mtime)}}}))
console.log(`Precompressed ${files.length} static text files; original bytes preserved.`)
