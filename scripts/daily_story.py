import datetime, json, os, re
from pathlib import Path

# High-retention, fact-grounded local story library. Keep history and business pools separate.
# Each script opens with a curiosity gap, delivers a clear payoff, and avoids presenting
# disputed explanations as proven facts.
history_stories = [
    ("The Roman Concrete That Heals Itself",
     "Some Roman harbor structures have survived seawater for nearly two thousand years. Why? Researchers studying Roman concrete found that its ingredients and chemistry differ from many modern mixes. Lime-rich chunks can help reactions continue when cracks form, potentially sealing tiny fractures. It is not magic, and not every Roman structure lasted—but ancient builders created a material whose durability scientists are still studying.",
     "Roman concrete ancient harbor;Roman Pantheon concrete;ancient Roman harbor ruins"),
    ("The War Australia Lost to Emus",
     "In 1932, Australian farmers faced huge flocks of emus damaging crops. Soldiers were sent with machine guns to help, but the birds scattered, moved quickly, and proved difficult to control. The operation became known as the Great Emu War. It was not a formal war between countries, but a real pest-control effort that became famous for its awkward results.",
     "Great Emu War 1932 Australia;emu flock Western Australia;Australian wheat field 1930s"),
    ("The City Buried by a Volcano—and Preserved",
     "When Mount Vesuvius erupted in AD 79, ash and volcanic material buried Pompeii. The disaster killed residents, but it also preserved buildings, wall paintings, shops, and even graffiti. Archaeologists can read ordinary messages scratched into walls, from political slogans to jokes and advertisements. Pompeii is more than a frozen disaster: it offers an unusually intimate glimpse into everyday Roman life.",
     "Pompeii preserved Roman street;Pompeii ancient graffiti wall;Mount Vesuvius Pompeii ruins"),
    ("The Viking Colony That Vanished from Greenland",
     "Norse settlers established communities in Greenland around a thousand years ago and survived there for centuries. Eventually, their settlements disappeared. Climate shifts, changing trade, economic pressures, and relations with Inuit communities may all have mattered, but historians do not have one definitive explanation. The mystery is not that Vikings suddenly vanished overnight—it is how a society adapted for generations and then failed to endure.",
     "Norse Greenland settlement ruins;Hvalsey church Greenland;Viking Greenland archaeological site"),
    ("The Wave of Molasses That Hit Boston",
     "In 1919, a huge storage tank burst in Boston and sent a wave of molasses through nearby streets. The sticky flood damaged buildings and killed 21 people. It sounds like a cartoon disaster, but it was deadly and led to years of legal disputes. The lesson is grim: industrial accidents can happen when engineering, inspection, and public safety fail—not only when the hazard looks dangerous.",
     "Boston Molasses Flood 1919 historical photograph;North End Boston 1919;molasses storage tank historical"),
    ("The Ancient Computer Pulled from the Sea",
     "A shipwreck near the Greek island of Antikythera yielded a corroded lump that looked like scrap metal. Inside were precisely arranged gears. Researchers eventually found that the device could track astronomical cycles and predict eclipses. Built more than two thousand years ago, it was far more sophisticated than many people expect from the ancient world. It did not do everything a modern computer does—but it changed the history of technology.",
     "Antikythera mechanism gears;Antikythera shipwreck archaeology;ancient Greek astronomy mechanism"),
    ("The Fake Fossil That Fooled Scientists",
     "For decades, the Piltdown Man discovery was presented as evidence of an important missing link in human evolution. In 1953, scientific tests showed the remains were a forgery made from a human skull and an orangutan jaw, with teeth altered to look ancient. The case embarrassed researchers, but it also became a lesson in science: extraordinary claims need independent testing, especially when evidence fits what people already want to believe.",
     "Piltdown Man fossil reconstruction;early human evolution fossil museum;British Museum paleoanthropology"),
    ("The Olympic Marathon That Turned into Chaos",
     "The 1904 Olympic marathon in St. Louis was a bizarre endurance race. Runners faced heat, dust, and poor conditions; one leading competitor received a car ride for part of the route before returning to the race, while another runner became seriously ill after taking a dangerous mixture. The event is remembered as a sporting farce, but it also helped show why endurance races need clear rules, medical planning, and reliable course supervision.",
     "1904 Olympic marathon St Louis;1904 Summer Olympics runners;historic Olympic marathon photograph"),
    ("Why an Ancient Army Terracotta Soldiers Look Different",
     "Thousands of life-sized terracotta soldiers guard the tomb complex of China's first emperor, Qin Shi Huang. Their faces and hairstyles vary, giving the impression of a vast army of individuals. Scholars debate how much reflects real portraiture versus standardized workshop production. What is clear is the scale: the figures required enormous organization, skilled labor, and a state capable of coordinating work on a breathtaking level.",
     "Terracotta Army Qin Shi Huang;Terracotta Warriors faces closeup;Xi'an terracotta army excavation"),
    ("The Medieval Book Nobody Can Read",
     "The Voynich Manuscript is an illustrated book filled with unfamiliar writing, strange plants, and curious diagrams. Researchers have proposed ciphers, invented languages, and other explanations, but no interpretation has achieved broad acceptance. It is tempting to call it alien or magical, yet there is no evidence for that. The real puzzle is more interesting: a physical historical book exists, but its text remains undeciphered.",
     "Voynich manuscript pages;Voynich manuscript botanical illustration;medieval manuscript closeup"),
    ("The Radio Signal That Lasted 72 Seconds",
     "In 1977, a radio telescope detected a strong, narrowband signal from space that lasted about 72 seconds. An astronomer marked the printout with the word 'Wow!' The signal was never confirmed again, so scientists cannot say it came from aliens. It remains unexplained, not proof of extraterrestrial life. The distinction matters: a strange observation can be exciting without proving the most dramatic theory.",
     "Wow signal original printout;Big Ear radio telescope;radio telescope night sky"),
    ("The Ship Found Drifting Without Its Crew",
     "In 1872, the merchant ship Mary Celeste was found adrift in the Atlantic with no crew aboard. Much of its cargo remained, and there was no confirmed sign of a violent struggle. The lifeboat was missing. Over time, theories multiplied, but none has been proven to explain exactly what happened. The mystery endures partly because the evidence is incomplete—and incomplete evidence leaves room for stories to grow.",
     "Mary Celeste historic sailing ship;19th century merchant ship Atlantic;Mary Celeste archival illustration"),
    ("The Desert Drawings Best Seen from the Sky",
     "Across Peru's Nazca Desert are enormous lines and figures made by clearing away dark stones to reveal lighter ground. Some depict animals, while others form long geometric patterns. Many can be appreciated best from above. Researchers connect them to ritual landscapes and water-related beliefs, but their exact purposes varied or remain debated. Their scale is astonishing, yet the people who made them did not need aircraft to create them.",
     "Nazca Lines hummingbird aerial;Nazca Lines Peru desert;Nazca geoglyph spider"),
    ("The Colony That Left One Strange Word",
     "In 1587, English settlers established a colony on Roanoke Island. When a later expedition returned, the settlement was deserted. The word 'CROATOAN' had been carved into a post, but there was no definitive record of what happened to everyone. Some settlers may have joined nearby Indigenous communities. The evidence does not prove a single dramatic ending, which is why the Lost Colony still fascinates historians.",
     "Roanoke colony historical illustration;Roanoke Island North Carolina map;Elizabethan sailing ship"),
]

business_stories = [
    ("Coca-Cola Changed Its Formula—and Customers Revolted",
     "In 1985, Coca-Cola replaced its original formula with New Coke after taste tests suggested people preferred a sweeter version. The reaction was intense: many customers wanted the old drink back. The company restored the original as Coca-Cola Classic months later. The episode shows why a product decision cannot rely on taste tests alone. Habit, identity, nostalgia, and the feeling of being heard can matter just as much.",
     "New Coke 1985 can;classic Coca-Cola bottles vintage;1980s Coca-Cola advertising"),
    ("The Phone Giant That Missed the Smartphone Shift",
     "Nokia once dominated mobile phones around the world. But when smartphones changed what customers expected—touchscreens, apps, and flexible software—the company struggled to respond quickly enough. Its decline had several causes, not one bad decision, but the shift exposed a brutal business truth: leadership in yesterday's market does not guarantee leadership tomorrow. Companies must keep adapting even when their current product seems unbeatable.",
     "Nokia classic mobile phone;early touchscreen smartphone;mobile phone store evolution"),
    ("How LEGO Nearly Ran Out of Bricks",
     "LEGO became famous for its colorful building bricks, but in the early 2000s the company faced serious financial trouble after expanding into too many activities and products. It refocused on its core building system, improved operations, and made choices more carefully. The turnaround was not simply about selling more toys; it involved understanding what customers valued and controlling complexity. Growth can hurt a company when it loses sight of its strengths.",
     "LEGO classic bricks colorful;LEGO factory production;LEGO building sets shelves"),
    ("Kodak Invented a Digital Camera—Then Hesitated",
     "Kodak engineer Steven Sasson built an early self-contained digital camera prototype in 1975. Kodak had helped create the technology, yet the company later struggled as digital photography transformed its film business. It is too simple to say leaders ignored one invention; Kodak did invest in digital, but replacing a profitable core business was difficult. The case shows how a company can understand a new technology and still struggle to adapt its business model.",
     "Steven Sasson early digital camera;Kodak film camera vintage;digital photography transition"),
    ("Netflix Offered to Sell to Blockbuster",
     "Netflix co-founder Reed Hastings has said Netflix proposed a partnership or sale to Blockbuster in 2000, when Netflix was still small. Blockbuster did not take the opportunity, and streaming later transformed how people watched entertainment. The story is often simplified into one foolish meeting, but the deeper point is that business models change: late fees and physical stores once mattered, while convenient digital access became increasingly important.",
     "Netflix DVD envelope vintage;Blockbuster video store 2000s;streaming television remote"),
    ("The Startup That Sold a Blood-Test Dream",
     "Theranos promised to run many medical tests using only a tiny amount of blood. The promise attracted major investors and attention, but investigations found that the technology could not reliably deliver what the company claimed. Its founder was later convicted of fraud. The story is not a warning against ambitious science; it is a warning that impressive presentations and famous supporters are not substitutes for independently verified results.",
     "Theranos laboratory blood testing;medical laboratory testing equipment;Silicon Valley startup office"),
    ("Why Costco Keeps Its Hot Dog So Cheap",
     "Costco is famous for keeping its food-court hot dog and soda combo at a low price for decades. The item is not just a snack; it reinforces the store's value image and gives members a memorable reason to feel they are getting a deal. The exact financial contribution is not the whole story. Sometimes a product helps a business by strengthening loyalty and trust, not by maximizing its own margin.",
     "Costco food court hot dog combo;warehouse club shopping carts;Costco warehouse exterior"),
    ("The Vacuum Cleaner Built from 5,000 Prototypes",
     "James Dyson developed bagless vacuum technology after becoming frustrated with how conventional vacuum bags clogged. He has described making thousands of prototypes before bringing a successful design to market. The number is often repeated as a symbol of persistence, but the useful lesson is more specific: repeated experiments only help when each one teaches you something. Testing, measuring, and improving can turn a frustrating problem into a product people will pay for.",
     "James Dyson bagless vacuum prototype;vacuum cleaner engineering prototype;Dyson vacuum product design"),
    ("Why De Beers Helped Make Diamonds a Symbol of Love",
     "Diamonds have not always been the automatic choice for engagement rings. In the twentieth century, diamond marketing helped link the stone with romance, commitment, and permanence. The famous slogan 'A Diamond Is Forever' became part of that cultural story. Advertising did not create love, of course, but it helped shape what many buyers came to expect. Marketing can influence not only which product people buy, but what the product means to them.",
     "vintage diamond engagement ring advertisement;diamond cutting workshop;diamond jewelry display"),
    ("Nintendo Started with Playing Cards",
     "Nintendo did not begin as a video-game company. Founded in Japan in 1889, it originally produced handmade playing cards. Over time it explored other businesses before becoming a global name in games. Its history is a reminder that companies can reinvent themselves over generations. The trick is not to change randomly; it is to notice new opportunities and build capabilities that fit the customers and market of the time.",
     "Nintendo hanafuda playing cards;Nintendo retro game console;Nintendo video game history"),
    ("The Fast-Food Trick That Scaled a Small Restaurant",
     "McDonald's global growth was not just about a popular burger. The company refined a repeatable restaurant system, standardized processes, and expanded through franchising. A consistent customer experience made it easier to grow across locations. Scaling a business means turning what works in one place into a process other people can repeat—without letting quality collapse. A great product helps, but a repeatable operating system is what makes expansion possible.",
     "early McDonalds restaurant historic;fast food kitchen assembly line;McDonalds restaurant franchise"),
    ("The Retailer That Tried to Stop Discounting",
     "JCPenney changed its pricing strategy in 2012, moving away from frequent coupons and sales toward everyday pricing. Many shoppers were used to discounts and reacted poorly; sales fell, and the company later returned to more promotions. The lesson is not that discounts are always good. It is that customer habits are part of a business model. Changing prices also changes the experience customers believe they are buying.",
     "JCPenney department store vintage;retail sale coupons;department store checkout"),
    ("WeWork's Billion-Dollar Image Problem",
     "WeWork grew by renting office space and offering flexible work environments, but its valuation soared far beyond what its underlying economics could comfortably support. When investors scrutinized its finances, governance, and growth assumptions, confidence collapsed and its planned 2019 IPO was withdrawn. The story shows that a powerful brand and a big market narrative cannot replace sustainable unit economics, transparent leadership, and a business model that works beyond fundraising.",
     "WeWork coworking office interior;shared office workspace;WeWork office building sign"),
    ("Why Free Apps Still Need a Business Model",
     "A free app can attract millions of users and still lose money. Servers, support, development, and marketing all cost something, while only some users may pay. Successful freemium businesses make the free product useful but offer paid features that solve a meaningful extra problem. The key question is not only 'How many people signed up?' It is 'Can the business serve and retain customers at a cost the revenue can support?'",
     "mobile app subscription pricing screen;software team analytics dashboard;SaaS customer retention chart"),
]


# Newly researched additions (November 2026). Keep scripts self-contained and cautious:
# current-event claims are limited to facts supported by reputable reporting or official sources.
history_stories.extend([
    ("The Bomber That Landed With Nobody on Board",
     "A military aircraft landing without a pilot sounds impossible, but unmanned and remotely operated aircraft have made that idea real. Recent history Shorts have drawn attention to stories of aircraft returning after crews were lost or forced to abandon them. Before publishing this angle, distinguish a genuinely empty landing from an aircraft that was remotely controlled or recovered by autopilot. The bigger historical question is how aviation moved from human pilots toward increasingly automated flight.",
     "unmanned bomber aircraft historical;WWII bomber aircraft archival;military aircraft cockpit"),
    ("The 400-Year-Old Lock Finally Opened",
     "A brass combination lock recovered from the wreck of the merchant ship Ann Francis, which sank off Wales in 1583, resisted researchers for centuries. Modern imaging helped specialists study its tiny internal mechanism and work out a four-letter combination: ANCE. The letters have not produced a confirmed explanation of what the lock protected. It is a remarkable meeting of archaeology and technology: a small everyday object preserved a puzzle across four hundred years.",
     "Ann Francis shipwreck Elizabethan lock;16th century brass combination lock;micro CT scan antique lock"),
    ("Egypt's 2,600-Year-Old Structure Found Beneath the Delta",
     "At ancient Buto in Egypt's Nile Delta, researchers used satellite radar and electrical-resistivity methods to investigate a large buried structure beneath the ground. The remains are estimated to be about 2,600 years old and measure roughly 128 by 62 metres. The discovery does not mean an entire city suddenly appeared from space. It shows how remote sensing can guide archaeologists toward buried places before excavation begins—and how much of ancient Egypt may still lie hidden.",
     "Tell el Fara'in Buto Egypt archaeology;Egypt satellite archaeology radar;ancient Egyptian Wadjet temple"),
    ("The 4,700-Year-Old Shipwreck That Rewrites Trade History",
     "Off Turkey's Mediterranean coast, archaeologists identified a shipwreck that may date to between 2700 and 2400 BC. More than thirty ceramic jars and three stone anchors were recovered, while the wooden hull has not survived. The pottery suggests links between the Levant, Egypt, and Anatolia during the Early Bronze Age. Researchers are still studying residues inside some containers, so the ship's exact cargo remains uncertain. Even without its wood, the wreck offers a rare glimpse of trade in the age of the pyramids.",
     "Kekova 4700 year old shipwreck;Early Bronze Age ceramic jars;underwater archaeology Turkey"),
    ("A Drought Revealed a Lost Roman City",
     "When water levels fall, landscapes can reveal structures hidden for centuries. Recent drought conditions in Europe exposed remains associated with a lost Roman settlement, bringing ancient walls and traces of urban life back into view. Such discoveries need careful identification: a visible ruin is not automatically a newly found city, and archaeologists compare maps, materials, and historical records before naming a site. The striking lesson is that climate can uncover the past while also threatening the archaeological remains it exposes.",
     "drought revealed Roman city Europe 2026;Roman ruins exposed drought;ancient Roman city aerial"),
    ("The Viking Hoard Hiding a Rare St Olaf Coin",
     "A Viking-age hoard can reveal more than how much wealth one person buried. A recently highlighted find included a rare coin associated with St Olaf, a Norwegian king later remembered as a saint. Coins travelled across borders, carrying rulers' names, religious symbols, and evidence of trade. A single unusual piece can help researchers trace connections between communities that left few written records. The hoard's full meaning depends on its archaeological context, not just the treasure's market value.",
     "Viking hoard St Olaf rare coin;Viking silver hoard archaeology;medieval Norwegian coin"),
    ("The WWII Ship Still Holding 1,500 Tons of Explosives",
     "The American cargo ship SS Richard Montgomery sank in the Thames Estuary in 1944 with a huge cargo of munitions still aboard. In November 2026, engineers removed its three exposed masts as part of ongoing efforts to reduce risks around the wreck. The operation did not remove the explosives: officials have continued to monitor the dangerous site. It is an unsettling reminder that the Second World War has left hazards beneath the water, even close to busy modern communities.",
     "SS Richard Montgomery wreck Thames;Richard Montgomery mast removal 2026;Thames Estuary WWII shipwreck"),
    ("The Roman Cup That Made Water Look Like Magic",
     "Some ancient Roman glass changes colour depending on how light passes through it. The famous Lycurgus Cup can appear green in reflected light and reddish when light shines through it. Researchers link the effect to tiny particles of gold and silver embedded in the glass. It was not electricity or a hidden lamp: Roman craftspeople created an optical effect through remarkable control of materials. The cup shows how sophisticated ancient manufacturing could be.",
     "Lycurgus Cup Roman glass red green;Roman dichroic glass museum;ancient Roman glass closeup"),
    ("The Castle Hidden Inside Another Castle",
     "In parts of medieval Europe, later builders expanded fortifications around older strongholds. Archaeologists have recently highlighted a castle complex where one defensive structure was effectively concealed within another. These layered buildings are physical records of changing power: a new ruler might strengthen, replace, or enclose an earlier fortress rather than erase it. The exact story depends on the site, but the visual twist is irresistible—what looks like one castle can contain several centuries of conflict and construction.",
     "medieval castle hidden inside castle archaeology;European layered castle walls;medieval fortress aerial"),
    ("The Mysterious Moai That Emerged Again",
     "The giant stone figures of Rapa Nui, often called Easter Island, are known around the world. Recent reports described a moai becoming visible again in a changing landscape, drawing attention to how these monuments are affected by erosion, water, and shifting ground. The statues were created by the island's Polynesian communities, and their history is tied to complex social and ceremonial traditions. Avoid the myth that outsiders built them: the moai are a remarkable achievement of Rapa Nui people.",
     "Rapa Nui moai statue landscape;Easter Island moai archaeology;moai statue coastal erosion"),
    ("The Ancient Footprints That Changed a Migration Debate",
     "A set of ancient human footprints can preserve a moment that bones alone cannot: people walking across a landscape. New archaeological work reported in 2026 has renewed debate about when humans reached particular regions and how they moved through them. Footprints must be dated carefully, because the age of the surrounding sediment and the possibility of disturbance both matter. When the evidence holds up, a trackway can turn an abstract migration theory into a scene of real people crossing the ground.",
     "ancient human footprints archaeological site;prehistoric trackway excavation;human migration footprints"),
    ("The 1583 Shipwreck That Kept Its Secrets",
     "The merchant ship Ann Francis sank off the coast of Wales in 1583, carrying objects that have survived underwater for more than four centuries. Among them was a small brass combination lock that researchers recently studied with modern scanning methods. The lock's letters have been decoded, but what they were meant to secure is still unknown. Shipwreck archaeology is often like this: technology can reveal how an object worked, while the people who used it remain just out of reach.",
     "Ann Francis 1583 shipwreck archaeology;Elizabethan merchant shipwreck artifacts;Tudor brass artifacts"),
    ("The Ancient City That Was Bigger Than Its Ruins Suggested",
     "Archaeologists increasingly use satellite images, ground surveys, and geophysical instruments to map settlements without digging everywhere. At sites across the ancient world, these tools can reveal buried streets, walls, and buildings extending beyond the ruins visible above ground. A large outline is only the beginning: teams still need excavation and dating to understand what the structures were and when people used them. The new frontier of archaeology is not just finding lost cities—it is learning how to see beneath the soil responsibly.",
     "archaeological geophysical survey buried city;ground penetrating radar ancient ruins;ancient city excavation aerial"),
    ("Why the Nazca Lines Survived for Centuries",
     "Peru's Nazca Lines are enormous designs made by removing dark surface stones to expose lighter soil underneath. Their preservation is partly due to the region's exceptionally dry climate and limited vegetation, although weather and human activity still pose risks. New imaging methods continue to help researchers identify figures and map the landscape. The lines were made by people on the ground, not by aircraft or visitors from space. Their true achievement is the planning and cultural knowledge behind them.",
     "Nazca Lines Peru aerial;Nazca geoglyph desert preservation;Nazca Lines archaeological survey"),
])

business_stories.extend([
    ("The AI Spending Boom That Started Scaring Investors",
     "The companies building artificial intelligence need enormous amounts of computing power, and that means expensive chips, buildings, electricity, and debt. In November 2026, investors became more cautious about whether the returns will justify the spending. That does not mean AI demand has disappeared: construction firms still report strong projects, while lenders are watching weaker developers more closely. The business question is simple but huge: who will earn enough from AI to pay for the infrastructure being built today?",
     "AI data center construction;GPU server racks;stock market technology trading floor"),
    ("Why an AI Data Center Can Cost Billions",
     "An AI data center is not just a warehouse full of computers. It needs specialized power systems, cooling, backup equipment, networking, land, and highly expensive accelerators. Bank of America research estimated global data-center spending could reach one trillion dollars in 2026 and rise further by 2028. Those are forecasts, not guaranteed outcomes. The opportunity is enormous for builders and equipment suppliers, but the costs create a difficult question: how quickly can customers turn all that computing capacity into revenue?",
     "AI data center power cooling infrastructure;data center server hall;industrial electrical transformers"),
    ("The $36 Billion Egyptian Bank Listing",
     "Banque du Caire began trading on Egypt's stock exchange in November 2026 after an offering worth more than 36.37 billion Egyptian pounds. The sale covered 45 percent of the bank, and the public tranche was reported as 27 times oversubscribed. That made it the largest IPO in the history of Egypt's capital market. An IPO does not guarantee future success, but it can broaden ownership, attract investors, and give a company new scrutiny from public markets.",
     "Banque du Caire IPO EGX November 2026;Egyptian Exchange trading floor;Banque du Caire building"),
    ("Why IFC Put $100 Million Into Banque du Caire",
     "The International Finance Corporation invested 100 million dollars in Banque du Caire's November 2026 IPO for an approximately seven percent stake. The IFC said the investment aims to help the bank expand financing for businesses and households, especially smaller companies. This is more than a headline about a foreign investor buying shares: development institutions often use investments to encourage private-sector lending and economic activity. The real test will be whether more firms can access useful finance and grow.",
     "IFC Banque du Caire investment;small business owner Egypt;Banque du Caire branch"),
    ("The World Bank's $1 Billion Bet on Egypt's Reforms",
     "In November 2026, the World Bank signed a one-billion-dollar financing agreement with Egypt linked to reforms, private-sector participation, and a greener economy. A financing deal is not the same as a billion dollars appearing in every business owner's account. It is a policy and funding program whose impact depends on implementation, conditions, and how projects translate into jobs and investment. The important business question is whether reforms make it easier for private companies to compete, expand, and hire.",
     "World Bank Egypt financing agreement 2026;Egypt business district Cairo;Egypt renewable energy infrastructure"),
    ("Why Builders Are Getting Pickier About AI Projects",
     "The AI data-center boom has created major construction opportunities, but not every project is equally safe. In November 2026, construction giant Skanska said it was becoming more selective, paying closer attention to whether newer developers had the financing and execution ability to finish projects. Demand can be real while individual companies still fail. For suppliers, contractors, and lenders, the lesson is to check who is paying, how the project is funded, and whether the promised facility can actually be delivered.",
     "Skanska data center construction;AI data center building site;construction cranes industrial project"),
    ("The Side Hustle Turning Designs Into Products",
     "Print-on-demand lets a seller upload a design and offer it on shirts, mugs, or posters without buying large amounts of inventory first. A supplier prints and ships an item after a customer orders it. That lowers the upfront stock risk, but it does not make the business effortless: sellers still need original designs, customer service, marketing, and enough margin to cover production and advertising. The real advantage is testing demand before committing money to inventory.",
     "print on demand t shirt production;custom mug printing business;online store product mockups"),
    ("Why Secondhand Shopping Became a Business",
     "Resale businesses turn used clothing, electronics, and household goods into products with a second life. Their appeal can come from lower prices, rare finds, and growing interest in re-use. But a resale operation still needs sourcing, inspection, cleaning, photography, pricing, and reliable delivery. A cheap item is not automatically profitable if it takes too long to prepare or ship. The strongest sellers build trust by showing condition honestly and making the buying process simple.",
     "secondhand clothing thrift store racks;resale business product photography;vintage clothing store"),
    ("The New Business Race: AI Agents for One Industry",
     "Instead of building one AI assistant for everyone, some startups focus on a narrow job in a specific industry—such as processing invoices, reviewing insurance claims, or helping schedule field services. A specialized tool can be easier to measure because it targets one costly workflow. But businesses will only keep paying if the system is accurate, secure, and fits existing operations. The opportunity is not simply replacing workers with chatbots; it is removing repetitive work without creating expensive mistakes.",
     "AI workflow automation business dashboard;industrial operations software;invoice processing office"),
    ("Why AI Companies Need More Than Users",
     "A technology startup can attract millions of users and still struggle to become a durable business. AI services have ongoing costs: computing, data, engineering, security, and customer support. If customers pay less than it costs to serve them, growth can make losses larger rather than smaller. Investors are increasingly asking how a company will turn usage into recurring revenue and positive margins. In the AI economy, attention is valuable—but sustainable unit economics matter more.",
     "AI startup engineers office;cloud computing server infrastructure;software business financial dashboard"),
    ("The Hidden Business Behind Every AI Prompt",
     "When someone sends a prompt to an AI service, computers in a data center process the request and use electricity, cooling, networking, and expensive hardware. At massive scale, small per-request costs add up. Providers try to reduce those costs through more efficient models and better hardware utilization, while customers compare price, speed, and quality. The business behind a simple chat window is an infrastructure operation—and its economics help determine which AI products can survive.",
     "AI inference GPU server racks;data center cooling pipes;AI cloud computing infrastructure"),
    ("Why Small Businesses Are Testing Automation",
     "A small company may not need a complicated AI strategy. It may simply want fewer missed customer messages, faster appointment reminders, or invoices entered without repetitive typing. Automation can save time, but only when the process is clear and exceptions are handled safely. A poorly configured bot can frustrate customers or create costly errors. The best starting point is usually one repetitive task with measurable time savings—not replacing an entire business with software.",
     "small business owner using laptop;customer service automation dashboard;small business invoice workflow"),
    ("The Subscription Trap: When Cheap Software Gets Expensive",
     "A business may sign up for several low-cost software subscriptions, each seeming harmless on its own. Over time, overlapping tools, unused seats, and automatic renewals can create a surprisingly large bill. The answer is not to cancel every subscription; it is to review who uses each tool, what work it replaces, and whether the value exceeds the cost. For software companies, retention depends on proving that customers still need the product after the first month.",
     "SaaS subscription management dashboard;business expense review laptop;software billing analytics"),
    ("The Business Lesson From Companies That Ignore Their Core",
     "A company can grow quickly by adding products, opening new divisions, and chasing every opportunity. But each new activity adds complexity, costs, and management attention. Businesses that lose clarity about their strongest customer promise can become harder to operate and harder to explain. A disciplined strategy asks what the company does unusually well, which customers value it, and what should be stopped. Sometimes the most profitable growth decision is choosing not to expand.",
     "business strategy planning team;company operations warehouse;corporate product portfolio meeting"),
])

channel = os.environ.get("CHANNEL_NAME", "history").strip().lower()
if channel not in ("history", "business"):
    raise SystemExit("CHANNEL_NAME must be history or business")
channel_stories = history_stories if channel == "history" else business_stories

def normalize_topic(value):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).split())


ledger_path = Path("state/published") / (channel + ".json")
ledger = {"legacy_blocked_topics": [], "entries": []}
if ledger_path.is_file():
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit("Could not read the durable duplicate ledger: " + str(exc))

used_topics = set()
for value in ledger.get("legacy_blocked_topics", []):
    if value:
        used_topics.add(normalize_topic(value))
for entry in ledger.get("entries", []):
    for value in (entry.get("topic"), entry.get("seed_topic")):
        if value:
            used_topics.add(normalize_topic(value))

available_stories = [
    story for story in channel_stories
    if normalize_topic(story[0]) not in used_topics
]

if not available_stories:
    raise SystemExit(
        f"No unused reviewed local stories remain for channel '{channel}'. "
        "Add more reviewed stories before the next run; no AI API fallback is configured."
    )

run_number = os.environ.get("GITHUB_RUN_NUMBER", "").strip()
if run_number.isdigit() and int(run_number) > 0:
    rotation_index = (int(run_number) - 1) % len(available_stories)
    rotation_source = "unused reviewed local story pool"
else:
    rotation_index = 0
    rotation_source = "first unused reviewed local story"
title, video_script, image_searches = available_stories[rotation_index]

with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as env:
    env.write("CHANNEL_NAME=" + channel + "\n")
    env.write("STORY_TOPIC=" + title + "\n")
    env.write("STORY_SEED_TOPIC=" + title + "\n")
    fallback_question = (
        f"What do you think really happened in {title}?"
        if channel == "history" else
        f"Would you have made the same decision in {title}?"
    )
    env.write("CTA_COMMENT_QUESTION=" + fallback_question + "\n")
    env.write("IMAGE_SEARCHES=" + image_searches + "\n")
    if video_script:
        env.write("VIDEO_SCRIPT<<STORY_SCRIPT_EOF\n")
        env.write(video_script + "\n")
        env.write("STORY_SCRIPT_EOF\n")

print("Today's channel: " + channel)
print("Unused reviewed local stories: " + str(len(available_stories)))
print("Rotation source: " + rotation_source)
print("Today's local topic: " + title)
