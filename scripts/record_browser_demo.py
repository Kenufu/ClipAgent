"""Record real UI interactions against an isolated, unmodified ClipAgent backend.

Optional dependency: playwright==1.56.0, installed Chrome, playwright install ffmpeg.
Start: python -m scripts.record_browser_demo --serve (port 8770 by default).
Record: python -m scripts.record_browser_demo --source sample_data/nasa/astronaut-training.mp4.
No network routes, model outputs, job states or application results are mocked.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'deliverables/demo'
EVIDENCE = ROOT / 'evaluation/browser_results'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def serve(port):
    from clipagent import config
    config.JOBS = ROOT / 'data/recording-demo/jobs'
    config.DATABASE = ROOT / 'data/recording-demo/jobs.sqlite3'
    os.environ['HF_HUB_OFFLINE'] = '1'
    import uvicorn
    import app
    uvicorn.run(app.app, host='127.0.0.1', port=port, log_level='warning')


async def record(args):
    from playwright.async_api import async_playwright, expect
    OUT.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    errors, network, marks, snapshots, checks = [], [], [], {}, []
    base = f'http://127.0.0.1:{args.port}'
    source = args.source.resolve()
    assert source.is_file(), source
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(channel='chrome', headless=True)
        context = await browser.new_context(viewport={'width': 1440, 'height': 900},
            record_video_dir=str(OUT / 'raw'), record_video_size={'width': 1440, 'height': 900},
            accept_downloads=True, locale='zh-CN')
        # A visible cursor is an instructional annotation only; no product state is changed.
        await context.add_init_script("""addEventListener('DOMContentLoaded', () => {
          const dot = document.createElement('div'); dot.id = 'recording-cursor';
          dot.style.cssText = 'position:fixed;width:18px;height:18px;border:2px solid #ffe18a;border-radius:50%;pointer-events:none;z-index:2147483647;left:-40px;top:-40px;box-shadow:0 0 0 2px #0008;';
          document.body.append(dot);
          addEventListener('mousemove', e => {dot.style.left = (e.clientX-9)+'px';dot.style.top=(e.clientY-9)+'px';});
          addEventListener('mousedown', () => dot.style.background = '#ffe18a88');
          addEventListener('mouseup', () => dot.style.background = 'transparent');
        });""")
        started = time.monotonic()
        page = await context.new_page()
        # Chrome 157's headless screencast reserves 87px of outer-window chrome
        # even with an emulated 900px viewport. Leave room to capture the bottom
        # command bar; screenshots alone do not reveal this recorder limitation.
        session = await context.new_cdp_session(page)
        window = await session.send('Browser.getWindowForTarget')
        await session.send('Browser.setWindowBounds', {'windowId': window['windowId'],
            'bounds': {'width': 1440, 'height': 987}})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('response', lambda response: network.append({'url': response.url.replace(base, ''), 'status': response.status}))
        page.set_default_timeout(20000)

        def mark(title, detail):
            marks.append({'start': round(time.monotonic() - started, 3), 'title': title, 'detail': detail})
            print(title, flush=True)

        async def click(selector):
            target = page.locator(selector)
            await target.scroll_into_view_if_needed()
            box = await target.bounding_box()
            await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=18)
            await page.wait_for_timeout(350)
            await target.click()

        async def ready(job_id, minimum_version=1):
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                job = await (await context.request.get(f'{base}/api/jobs/{job_id}')).json()
                if job['status'] == 'failed':
                    raise AssertionError(job['error'])
                if job['status'] in ('complete', 'needs_review') and job['version'] >= minimum_version:
                    await expect(page.locator('#revise-button')).to_be_enabled(timeout=20000)
                    await expect(page.locator('#output-summary')).to_contain_text(f"版本 {job['version']}")
                    return job
                await page.wait_for_timeout(500)
            raise AssertionError('Job did not finish within 180 seconds')

        async def snapshot(name, job):
            clean = json.loads(json.dumps(job).replace(str(ROOT), '<PROJECT>'))
            snapshots[name] = clean
            await page.screenshot(path=str(EVIDENCE / f'{name}.png'))

        try:
            await page.goto(base)
            await page.wait_for_load_state('networkidle')
            mark('01 / 新建项目', '真实浏览器操作 · NASA真人视频61秒节选 · 本地CPU运行')
            await page.wait_for_timeout(2500)
            await click('#project-drawer-toggle')
            await click('#new-edit-button')
            await page.locator('#files').set_input_files(source)
            await page.wait_for_timeout(1000)
            await page.locator('#instruction').press_sequentially(
                'Create a 20-30 second recap covering training and spacewalks; export landscape with subtitles.', delay=35)
            await page.locator('#topics').fill('training, spacewalks')
            await page.locator('#target_seconds').fill('25')
            await page.locator('input[name="aspect"][value="16:9"]').check()
            await page.wait_for_timeout(2200)
            mark('02 / 自动处理', '上传 → 语音转录 → 选择片段 → 渲染 → 验证；状态来自真实后端')
            async with page.expect_response(lambda r: r.url == base + '/api/jobs' and r.request.method == 'POST') as response:
                await click('#edit-form button[type="submit"]')
            created = await (await response.value).json()
            job_id = created['id']
            await expect(page.locator('#job-view')).to_be_visible()
            if await page.locator('#project-drawer-toggle').get_attribute('aria-expanded') == 'true':
                await click('#project-drawer-close')
            await click('#tab-activity')
            first = await ready(job_id)
            assert first['status'] == 'complete', first['report']
            assert all(t['verified'] for t in first['report']['topic_evidence'])
            checks.append('Real MP4 upload opens the new job and completes CPU transcription/render/decode')
            await snapshot('01_initial', first)
            await page.wait_for_timeout(3500)

            mark('03 / 原素材与证据', '查看真人出镜原素材，再查看带时间戳的语音来源')
            await click('.source-item')
            await page.locator('#source-video').evaluate('(v) => {v.muted=true; return v.play();}')
            await page.wait_for_timeout(5000)
            await page.locator('#source-video').evaluate('(v) => v.pause()')
            await click('#tab-evidence')
            await page.wait_for_timeout(4500)
            await click('#tab-checks')
            await expect(page.locator('#checks-count')).to_have_text('全部通过')
            await page.wait_for_timeout(4000)
            await click('#monitor-output')
            await page.locator('#preview-video').evaluate('(v) => {v.muted=true; return v.play();}')
            await page.wait_for_timeout(5500)
            await page.locator('#preview-video').evaluate('(v) => v.pause()')

            mark('04 / 手动分割与裁剪', '点击时间尺定位 → 剪刀分割 → 属性面板调整入点')
            await click('#tab-properties')
            await click('.track-segment[data-index="0"]')
            first_duration = first['timeline'][0]['end'] - first['timeline'][0]['start']
            ruler = await page.locator('#timeline-ruler').bounding_box()
            cut = min(2.0, first_duration / 2)
            await page.mouse.click(ruler['x'] + 32 + cut*30, ruler['y'] + 10)
            await page.wait_for_timeout(1200)
            count = await page.locator('.track-segment').count()
            await click('#split-clip')
            await expect(page.locator('.track-segment')).to_have_count(count+1)
            await click('.track-segment[data-index="0"]')
            inp = page.get_by_role('spinbutton', name='片段 1 源入点 / 秒')
            await inp.fill(f"{first['timeline'][0]['start'] + .12:.2f}")
            await inp.press('Tab')
            await expect(page.locator('#save-timeline')).to_be_enabled()
            await page.wait_for_timeout(2500)
            # Move and restore via real controls, keeping the final narrative order.
            await page.get_by_role('button', name='向后移动', exact=True).click()
            await page.wait_for_timeout(1000)
            await page.get_by_role('button', name='向前移动', exact=True).click()
            await page.wait_for_timeout(1500)
            checks.append('Ruler seek, split, source-in adjustment, and move/restore operate on the draft')
            mark('05 / 重新渲染', '手动修改后重新生成MP4，并重新检查保留下来的语音证据')
            await click('#save-timeline')
            await click('#tab-activity')
            edited = await ready(job_id, first['version']+1)
            assert len(edited['timeline']) == count+1
            await snapshot('02_manual_edit', edited)
            await page.wait_for_timeout(3500)
            await click('#tab-checks')
            await page.wait_for_timeout(3500)

            mark('06 / 修改指令', '将必要主题改为spacewalks；复用转录结果，再次生成短片')
            await page.locator('#revision-text').press_sequentially(
                'Create a 15-25 second recap covering only spacewalks; export landscape.', delay=40)
            await page.wait_for_timeout(2000)
            await click('#revise-button')
            await click('#tab-activity')
            revised = await ready(job_id, edited['version']+1)
            assert revised['options']['topics'] == ['spacewalks']
            assert revised['transcript'] == first['transcript']
            assert revised['status'] == 'complete', revised['report']
            checks.append('Follow-up instruction reuses the exact transcript and changes the required topic')
            await page.wait_for_timeout(3500)
            await click('#tab-checks')
            await snapshot('03_revision', revised)
            await page.wait_for_timeout(3500)

            mark('07 / 导出成片', '下载真实生成的MP4与SRT；视频末尾附完整成片和原声')
            async with page.expect_download() as download:
                await click('#header-export')
            await (await download.value).save_as(OUT / 'NASA-edited.mp4')
            async with page.expect_download() as download:
                await click('#subtitle-link')
            await (await download.value).save_as(OUT / 'NASA-edited.srt')
            await page.wait_for_timeout(2500)
            checks.append('MP4 and SRT downloaded using the actual UI export buttons')

            mark('08 / 缺失主题检查', '提出素材中不存在的主题；检查器应明确显示待检查，不假称完成')
            await page.locator('#revision-text').press_sequentially(
                'Create a 15-25 second recap covering quantum teleportation; export landscape.', delay=30)
            await click('#revise-button')
            failed_topic = await ready(job_id, revised['version']+1)
            assert failed_topic['status'] == 'needs_review'
            assert not failed_topic['report']['topic_evidence'][0]['verified']
            await click('#tab-checks')
            await expect(page.locator('#checks')).to_contain_text('缺失')
            await snapshot('04_missing_topic', failed_topic)
            await page.wait_for_timeout(5000)
            checks.append('Absent quantum teleportation topic produces needs_review and visible missing evidence')
            mark('09 / 恢复可用成片', '恢复spacewalks剪辑；接下来播放导出的完整成片（原声）')
            await page.locator('#revision-text').fill('Create a 15-25 second recap covering only spacewalks; export landscape.')
            await click('#revise-button')
            restored = await ready(job_id, failed_topic['version']+1)
            assert restored['status'] == 'complete'
            await click('#tab-checks')
            await page.wait_for_timeout(3000)
            await snapshot('05_final_workspace', restored)
            assert not errors, errors
            await context.close()
            raw = await page.video.path()
            save(OUT / 'chapters.json', marks)
            save(EVIDENCE / 'snapshots.json', snapshots)
            save(EVIDENCE / 'network.json', network)

            # Additional responsive and drawer assertions outside the demonstration video.
            qa = await browser.new_context(viewport={'width': 1440, 'height': 900})
            qp = await qa.new_page()
            await qp.goto(base)
            await expect(qp.locator('#job-view')).to_be_visible()
            await qp.locator('#project-drawer-toggle').click()
            await expect(qp.locator('#project-drawer-toggle')).to_have_attribute('aria-expanded', 'true')
            await qp.reload()
            await expect(qp.locator('#project-drawer-toggle')).to_have_attribute('aria-expanded', 'true')
            await qp.keyboard.press('Escape')
            await expect(qp.locator('#project-drawer-toggle')).to_have_attribute('aria-expanded', 'false')
            checks.append('Project drawer open state persists across reload and Escape closes it')
            layouts = []
            for width, height in [(1440,900), (1280,720), (390,844)]:
                await qp.set_viewport_size({'width': width, 'height': height})
                await qp.wait_for_timeout(600)
                dimensions = await qp.evaluate('''() => ({width:innerWidth, height:innerHeight,
                    scrollWidth:document.documentElement.scrollWidth,
                    timeline:document.querySelector('.timeline-section').getBoundingClientRect().toJSON()})''')
                assert dimensions['scrollWidth'] <= width, dimensions
                monitor = await qp.locator('.video-shell').bounding_box()
                video = await qp.locator('#preview-video').bounding_box()
                assert abs(video['height']-monitor['height']) < 1, (monitor, video)
                assert abs(video['width']-monitor['width']) < 1, (monitor, video)
                if width >= 1280:
                    assert dimensions['timeline']['height'] >= (height-42)/3, dimensions
                    for selector in ['.source-bin', '.preview-section', '.inspector', '.timeline-section']:
                        box = await qp.locator(selector).bounding_box()
                        assert box['y'] >= 0 and box['y']+box['height'] <= height+1, (selector, box)
                layouts.append(dimensions)
                await qp.screenshot(path=str(EVIDENCE / f'layout-{width}.png'), full_page=True)
            checks.append('1440x900, 1280x720 and 390x844 layouts have no horizontal page overflow')
            checks.append('Video element fits its monitor at all three sizes, preserving the full image and controls')
            ranged = await qa.request.get(f'{base}/api/jobs/{job_id}/video', headers={'Range':'bytes=0-1023'})
            assert ranged.status == 206 and len(await ranged.body()) == 1024
            checks.append('Output MP4 Range request returns HTTP 206 and exactly 1024 requested bytes')
            await qa.close()
            summary = {'status':'passed', 'job_id':job_id, 'checks': checks, 'page_errors':errors,
                'browser':browser.version, 'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                'layouts':layouts, 'raw_recording':Path(raw).name,
                'limitations':['One selected public NASA video; not a representative benchmark.',
                    'Browser interactions are automated and recorded in real time. Only the cursor is annotated.',
                    'No mocked APIs, fixed transcripts, fake progress or substituted outputs.',
                    'UI recording has no captured audio; original output audio is included in the appended result.']}
            save(EVIDENCE / 'summary.json', summary)
            save(OUT / 'recording.json', {'raw_path':str(Path(raw).relative_to(ROOT)), 'job_id':job_id})
            print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
        except Exception as exc:
            save(EVIDENCE / 'last_error.json', {'error':str(exc), 'page_errors':errors, 'marks':marks})
            if not page.is_closed():
                await page.screenshot(path=str(OUT/'recording-error.png'))
            await context.close()
            raise
        finally:
            await browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--port', type=int, default=8770)
    parser.add_argument('--source', type=Path, default=ROOT/'sample_data/nasa/astronaut-training.mp4')
    args = parser.parse_args()
    serve(args.port) if args.serve else asyncio.run(record(args))
