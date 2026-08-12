import QRCode from 'qrcode';

async function runTests() {
  const tests = [
    { name: 'Normal URL', data: 'https://google.com' },
    { name: 'URL with params', data: 'https://example.com/search?q=hello%20world&page=2#top' },
    { name: 'Internationalized URL (Punycode)', data: 'https://xn--trke-1oa3a.com' },
    { name: 'UTF-8 URL', data: 'https://münchen.de' },
    { name: 'Japanese characters', data: 'https://ja.wikipedia.org/wiki/メインページ' },
    { name: 'Very long URL (500 chars)', data: 'https://example.com/' + 'a'.repeat(500) }
  ];

  let allPassed = true;
  for (const t of tests) {
    try {
      const url = await QRCode.toDataURL(t.data, { errorCorrectionLevel: 'M' });
      if (!url.startsWith('data:image/png;base64,')) {
        console.error(`Failed ${t.name}: output is not a data URL.`);
        allPassed = false;
      } else {
        console.log(`Passed: ${t.name} (length: ${url.length})`);
      }
    } catch (e) {
      console.error(`Error on ${t.name}:`, e.message);
      allPassed = false;
    }
  }

  if (allPassed) {
    console.log('ALL TESTS PASSED SUCCESSFULLY! 100% WORKING.');
  } else {
    console.log('SOME TESTS FAILED.');
    process.exit(1);
  }
}

runTests();
