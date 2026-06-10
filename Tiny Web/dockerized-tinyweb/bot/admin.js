let app = require('express')()
let { firefox} = require('playwright')

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms))
}

// везде в коде бота заменил localhost на vuln-server

let botBusy = false

app.get('/bot', (req, res) => res.send(`
    <form action="/bot/run" method="GET">
        URL: <input name="url" placeholder="http://vuln-server:8080/example" style="width: 400px;">
        <button>Run</button>
    </form>
`))

app.get('/bot/run', async (req, res) => {
    const targetUrl = req.query.url
    if (typeof targetUrl === 'string' && !targetUrl.startsWith('http://vuln-server:8080')) {
        return res.send('invalid url')
    }


    if (!botBusy) {
        botBusy = true
        try {
            let browser
            const launchOptions = {
                headless: true
            }

            browser = await firefox.launch(launchOptions)

            const page = await browser.newPage()
            await page.goto('http://vuln-server:8080', {waitUntil: 'domcontentloaded'});
            await page.evaluate(flag => document.cookie = "flag="+flag, process.env.FLAG)
            await page.goto(targetUrl, {
                waitUntil: 'domcontentloaded',
                timeout: 15000
            })
            await sleep(30000)
            await browser.close()
        } catch (err) {
            console.error(err)
        } finally {
            botBusy = false
        }
    } else {
        return res.send('pls wait')
    }

    return res.send('ok')
})

app.listen(8081)
