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
    ("The WWII Bomber That Crashed With No Crew Aboard",
     "On November 23, 1944, a damaged American B-17 Flying Fortress came down in a field in Belgium with nobody aboard. Soldiers who inspected it found the engines still running and the crew missing. The story became known as the Phantom Fortress. Later accounts said the crew had set the aircraft on autopilot and parachuted out, but details in the surviving reports do not perfectly match. The remarkable landing was real enough to investigate; the mystery grew as versions of the story changed.",
     "Phantom Fortress B-17 Belgium 1944;B-17 Flying Fortress WWII;91st Bombardment Group B-17"),
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
    ("The Jordan Valley Site That May Rewrite Human Migration",
     "A site called 'Ubeidiya in the Jordan Valley has been dated to about 1.9 million years ago, older than researchers previously thought. Scientists combined several dating methods, including analysis of buried rocks, fossil shells, and ancient magnetic-field records. The site contains stone tools and animal fossils, making it important evidence for early human movement beyond Africa. Researchers say the revised age may point to earlier or overlapping migration waves—but it does not identify exactly which human species made every tool.",
     "Ubeidiya archaeological site Jordan Valley;1.9 million year old stone tools;early human migration excavation"),
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


# Additional evergreen reviewed stories added to support twice-daily publishing.
# These are deliberately non-breaking, fact-grounded topics; no AI text fallback.
history_stories.extend([
    ("The Printing Press That Changed Europe",
     "In the mid-fifteenth century, Johannes Gutenberg developed a European system for printing books with movable metal type. Printing itself had older roots in East Asia, but Gutenberg's combination of reusable type, ink, and a press helped books be produced in much larger numbers. Ideas could travel farther, and texts became easier to compare and preserve. The change was not instant or universal, but it transformed how knowledge circulated.",
     "Gutenberg printing press reconstruction;15th century movable metal type;early printed book pages"),
    ("The Message Hidden in the Rosetta Stone",
     "The Rosetta Stone carries the same decree in three scripts: hieroglyphic, Demotic, and ancient Greek. Because scholars could read Greek, the inscriptions gave them a crucial way to compare signs and meanings. Jean-François Champollion announced a major breakthrough in deciphering Egyptian hieroglyphs in 1822. The stone did not translate every inscription by itself, but it helped unlock a writing system that had been unreadable to scholars for centuries.",
     "Rosetta Stone British Museum;Egyptian hieroglyphics closeup;Champollion hieroglyphic notes"),
    ("The Lighthouse Lens That Made Light Travel Farther",
     "Before modern electric lamps, lighthouse keepers needed a way to make a modest flame visible over long distances. French physicist Augustin-Jean Fresnel developed a special lens made from concentric rings that could gather and direct light efficiently. Fresnel lenses became a major improvement in maritime navigation. The clever part was not making the flame stronger; it was controlling where its light went.",
     "Fresnel lighthouse lens closeup;historic lighthouse lantern room;Fresnel lens prisms"),
    ("The Cable That Tried to Connect Two Continents",
     "In 1858, a submarine telegraph cable briefly connected North America and Europe, allowing messages to cross the Atlantic far faster than ships. The first cable failed after only a few weeks because its electrical performance and insulation could not withstand the demands placed on it. A more successful cable was laid in 1866. The breakthrough showed that global communication would depend not only on clever ideas, but on engineering that survived the real ocean.",
     "1858 Atlantic telegraph cable illustration;Victorian telegraph operators;transatlantic cable ship"),
    ("The Manuscripts That Survived in Timbuktu",
     "For centuries, scholars and families in Timbuktu preserved handwritten works on law, astronomy, mathematics, history, and religion. The manuscripts reflect West Africa's long intellectual and trading networks, not an isolated outpost cut off from the world. Many collections were kept in private homes and libraries, where heat, dust, conflict, and time created serious preservation challenges. Their survival reminds us that written knowledge has been protected by communities as well as famous institutions.",
     "Timbuktu historic manuscripts;Mali Arabic manuscript pages;Sankore Mosque Timbuktu"),
    ("The Explorer Who Reached the South Pole First",
     "In December 1911, Norwegian explorer Roald Amundsen and his team reached the geographic South Pole ahead of a British expedition led by Robert Falcon Scott. Amundsen's success depended on careful planning, skis, dogs, and lessons learned from Arctic travel. Scott's party reached the pole weeks later but died on the return journey. The race is often told as a contest of bravery, yet preparation, logistics, and adapting equipment to the environment were decisive.",
     "Amundsen South Pole expedition 1911;historic Antarctic tent expedition;Roald Amundsen polar photograph"),
    ("The Ship Trapped in Antarctic Ice",
     "In 1915, Ernest Shackleton's ship Endurance became trapped in Antarctic sea ice and was eventually crushed. The crew escaped onto the ice and later reached Elephant Island; Shackleton and a small group then made a dangerous boat journey to seek help. Remarkably, all members of the expedition survived. Their rescue was not a single miracle moment but a long sequence of decisions, endurance, and leadership under extreme conditions.",
     "Endurance expedition ship ice 1915;Ernest Shackleton expedition crew;Elephant Island Antarctica"),
    ("The City That Built a Modern Sewer System",
     "A severe outbreak of cholera and the polluted River Thames pushed Victorian London to rethink sanitation. Engineer Joseph Bazalgette led the construction of a vast sewer network that carried waste away from crowded districts. The system was built in stages and required enormous tunnels, pumping stations, and public investment. It became a major example of infrastructure that people rarely notice when it works, even though it protects millions.",
     "Joseph Bazalgette London sewer;Victorian London sewer tunnel;Crossness pumping station"),
    ("The Ancient Library We Cannot Rebuild",
     "The Library of Alexandria became a symbol of ancient scholarship, but its history is more complicated than the popular story of one fire destroying all knowledge. The institution changed over time, and the loss of books likely happened through multiple episodes of political upheaval, neglect, and damage. Scholars gathered texts from across the Mediterranean world, making the library an ambitious center of learning. Its real story is a warning about how fragile knowledge institutions can be.",
     "Ancient Library of Alexandria reconstruction;Alexandria ancient harbor illustration;ancient Greek papyrus scrolls"),
    ("The Sailors Who Navigated Without Compasses",
     "Polynesian navigators crossed vast stretches of the Pacific using detailed knowledge of stars, ocean swells, winds, birds, and cloud patterns. Their voyages connected islands separated by thousands of kilometres, long before satellite navigation or modern instruments. This was not guesswork: knowledge was taught, practiced, and refined across generations. The achievement shows that sophisticated navigation can be built from close observation of the natural world.",
     "Polynesian traditional voyaging canoe;wayfinding star navigation Pacific;Polynesian double hulled canoe"),
    ("The King Whose Pilgrimage Shook Gold Markets",
     "Mansa Musa ruled the Mali Empire in the fourteenth century, when West African gold and trade routes connected the region to North Africa and beyond. During his pilgrimage to Mecca, his large entourage passed through Cairo, where later accounts described substantial gold spending and its effect on local prices. Exact figures are uncertain, but the journey revealed Mali's wealth and international connections to observers far beyond West Africa.",
     "Mansa Musa Catalan Atlas;medieval Mali Empire map;Timbuktu historic trade routes"),
    ("The Scrolls Hidden Near the Dead Sea",
     "Beginning in 1947, ancient manuscripts were discovered in caves near Qumran by the Dead Sea. The Dead Sea Scrolls include biblical texts, community writings, and other works copied over centuries. They gave scholars an unusually rich window into Jewish life and religious thought in the Second Temple period. The scrolls did not answer every historical question, but they showed how varied texts and traditions were in the ancient world.",
     "Dead Sea Scrolls parchment;Qumran caves Dead Sea;Dead Sea Scrolls Hebrew manuscript"),
    ("The Explosion That Flattened a Canadian Harbor",
     "On December 6, 1917, two ships collided in Halifax Harbour, and one carried a large cargo of explosives. The resulting blast devastated nearby communities, killed almost two thousand people, and injured many more. The disaster led to major relief efforts and changes in how dangerous cargo and port emergencies were handled. It remains one of the largest non-nuclear explosions in history and a stark reminder of industrial risk.",
     "Halifax Explosion 1917 archival photograph;Halifax harbour historic ships;Halifax Explosion memorial"),
    ("The Eruption That Sent Ash Around the World",
     "In 1883, the volcanic island of Krakatoa erupted in Indonesia in a series of enormous explosions. The eruption generated tsunamis, devastated nearby coastlines, and sent ash and gases high into the atmosphere. Reports of unusual sunsets appeared far from the eruption zone. The event became one of the best documented major volcanic disasters of its era, showing how a local geological event can have effects across the planet.",
     "Krakatoa 1883 eruption historical illustration;Krakatoa volcanic island;1883 volcanic ash atmosphere"),
    ("The Tunguska Blast That Flattened a Forest",
     "In June 1908, a huge explosion occurred over a remote region near the Tunguska River in Siberia. It flattened trees across a vast area, yet no large impact crater was found. The leading explanation is that an asteroid or comet fragment exploded in the atmosphere before reaching the ground. Scientists continue to study the event because it shows that even an object that breaks apart in the sky can release enormous energy.",
     "Tunguska 1908 flattened forest;Siberian taiga aerial forest;Tunguska expedition archival photo"),
    ("The Roman Road Network That Connected an Empire",
     "Roman roads were built for military movement, administration, trade, and communication. Some routes used carefully prepared foundations and durable surfaces, while bridges and milestones helped travelers cross and understand the network. Not every road was paved with large stone slabs, despite the familiar image. The system helped officials and armies move across a huge territory, and traces of many routes remain visible today.",
     "Roman road Appian Way;Roman road stone paving closeup;Roman milestone inscription"),
    ("The Medieval University That Outlasted Empires",
     "The University of Bologna developed in the late eleventh century and became one of Europe's earliest universities. Students and teachers organized around the study of law, and the institution evolved through changing political systems and centuries of scholarship. Medieval universities were not identical to modern campuses, but they created durable structures for teaching, debate, and recognized qualifications. Their influence can still be seen in how higher education is organized.",
     "University of Bologna historic archway;medieval university manuscript;Bologna old university hall"),
    ("The City That Became a Center of Ancient Paper",
     "The ancient city of Pergamon in Asia Minor became associated with parchment, a writing material made from prepared animal skin. The word 'parchment' is linked to the city's name, although the material was used in other places too. Parchment was durable and could be folded into book-like formats, helping manuscripts survive. The story is a reminder that technologies for storing information often evolve through practical improvements in materials.",
     "Pergamon ancient library ruins;parchment manuscript texture;ancient parchment codex"),
    ("The Fire That Rebuilt Chicago",
     "A major fire swept through Chicago in October 1871, destroying a large part of the city and leaving many people homeless. The causes were more complicated than the famous story about a cow and a lantern, which has never been proven. Rebuilding brought new construction methods, stronger fire regulations, and a wave of architectural experimentation. The disaster became part of the story of how a fast-growing city redesigned itself after catastrophe.",
     "Great Chicago Fire 1871 illustration;Chicago rebuilding 19th century;Chicago Water Tower historic"),
    ("The Greek Fire That Frightened Medieval Fleets",
     "Byzantine sources describe a naval incendiary weapon often called Greek fire, which could burn on water and was especially feared in sea battles. The exact formula has not survived, and historians debate how it was prepared and delivered. It was not a single magical substance that made the Byzantine Empire invincible. Its importance came from secrecy, specialized equipment, and the psychological effect of a weapon that opponents struggled to counter.",
     "Byzantine Greek fire medieval illustration;Byzantine dromon ship reconstruction;medieval naval battle art"),
])

business_stories.extend([
    ("How Toyota Made Small Improvements a Daily Habit",
     "Toyota became known for a production approach that emphasizes reducing waste, improving quality, and giving workers a role in spotting problems. The Toyota Production System developed over decades rather than appearing as one overnight invention. Ideas such as just-in-time production and continuous improvement influenced manufacturers around the world. Its deeper lesson is that efficiency comes from designing a system where problems are visible and people can fix them early.",
     "Toyota production line factory;Toyota lean manufacturing kanban;Japanese auto assembly workers"),
    ("The Sticky Note That Began as a Failed Glue",
     "In 1968, 3M scientist Spencer Silver developed an adhesive that stuck lightly and could be removed without leaving much residue. At first, it seemed to have no obvious use. Years later, colleague Art Fry found a way to use it for bookmarks that stayed in place. The Post-it Note became a major product because an unusual technical discovery met a practical everyday problem. Innovation sometimes depends on connecting ideas across teams.",
     "3M Post-it Notes original;Spencer Silver Art Fry Post-it;sticky notes office desk"),
    ("How IKEA Turned Flat Packs Into a Business Advantage",
     "IKEA built much of its model around furniture customers could transport and assemble themselves. Flat-pack design reduced shipping volume and made large-scale retail more practical, while showroom layouts helped shoppers imagine products in their homes. The approach also shifts some work to the customer, so clear instructions and product design matter. The business lesson is that packaging and logistics can be part of the product strategy, not just a delivery detail.",
     "IKEA flat pack furniture boxes;IKEA showroom interior;flat pack furniture assembly"),
    ("The Fashion Company That Made Speed Its Strategy",
     "Zara became known for responding quickly to changing fashion demand. Its model combines close attention to customer preferences, frequent product updates, and a supply chain designed to move selected items from idea to store relatively quickly. Speed does not mean every product is made locally or instantly; the company uses a mix of sourcing and distribution choices. Its advantage comes from coordinating design, production, and stores as one operating system.",
     "Zara fashion retail store;fashion design studio clothing racks;garment distribution logistics"),
    ("The Delivery Network Built Around One Hub",
     "FedEx helped popularize an overnight delivery model built around a central air hub, where packages are sorted and transferred between flights. A hub-and-spoke network can connect many cities efficiently, but it depends on tight schedules, reliable sorting, and backup plans when weather or equipment disrupts operations. The innovation was not simply faster planes. It was a coordinated network that made a time-sensitive promise possible at scale.",
     "FedEx Memphis air hub night;parcel sorting conveyor belts;FedEx cargo aircraft"),
    ("The Coffee Chain That Sold a Place to Pause",
     "Starbucks grew by offering more than a cup of coffee: its stores were designed as comfortable places between home and work. The company expanded its menu, store formats, and brand experience while building a recognizable routine for customers. That positioning can create loyalty, but it also raises expectations about service, consistency, and atmosphere. A business can compete through the experience surrounding a product as much as through the product itself.",
     "early Starbucks coffee shop Seattle;Starbucks coffee bar interior;coffee barista espresso machine"),
    ("How Adobe Changed From Boxed Software to Subscriptions",
     "Adobe moved its major creative software products toward a subscription model through Creative Cloud, replacing the old pattern of occasional boxed upgrades. The transition gave the company more predictable recurring revenue and let customers receive ongoing updates. It also changed how users paid and raised concerns among customers who preferred permanent licenses. The shift shows that changing a business model can improve revenue stability while creating new customer-trust challenges.",
     "Adobe Creative Suite boxed software;Adobe Creative Cloud apps;graphic designer workstation"),
    ("The Outdoor Brand That Encouraged Repairs",
     "Patagonia built a reputation around durable outdoor clothing and environmental commitments. Its repair and resale initiatives encourage customers to keep products in use longer instead of automatically replacing them. That message can strengthen brand loyalty, but it also challenges the usual retail assumption that more frequent purchases are always better. The business question is whether a company can build long-term trust by aligning its operations with the values it promotes.",
     "Patagonia Worn Wear clothing repair;outdoor jacket repair workshop;Patagonia outdoor apparel store"),
    ("The Tire Company That Created a Travel Guide",
     "Michelin began publishing travel guides to encourage motorists to explore and, indirectly, use more tires. Over time, the guide developed restaurant ratings that became influential in the food world. The company turned a marketing idea into a trusted information product with a life beyond its original purpose. It is an unusual example of a brand building authority by helping customers do something related to its industry.",
     "Michelin Guide red book vintage;Michelin star restaurant kitchen;early automobile road travel"),
    ("The Sports Drink Brand Built on Event Marketing",
     "Red Bull grew by connecting its energy drink with high-energy sports, music, and adventurous events. Rather than relying only on traditional product advertising, the company invested in experiences and media that audiences wanted to watch. That strategy helped make the brand recognizable far beyond the supermarket shelf. The lesson is that content and community can become powerful marketing assets when they reinforce a clear brand identity.",
     "Red Bull Flugtag event;Red Bull air race aircraft;extreme sports event audience"),
    ("The Chip Company That Licensed Its Designs",
     "Arm became influential by licensing processor designs and intellectual property to companies that build their own chips. Instead of manufacturing every processor itself, Arm earns revenue through licensing and royalties as its architecture is used in phones, computers, cars, and other devices. This model allows broad adoption but requires strong technical standards and relationships with partners. It shows how a company can build a business around designs rather than factories.",
     "ARM processor chip closeup;semiconductor wafer fabrication;smartphone system on chip"),
    ("The Payment Network That Does Not Lend You Money",
     "Visa is often mistaken for a bank, but its core role is to operate a payment network that connects consumers, merchants, financial institutions, and processors. Banks typically issue the cards and manage customer credit or deposits, while the network helps authorize and route transactions. The distinction matters because a payment platform can earn value by connecting participants without directly lending to every cardholder.",
     "Visa payment card terminal transaction;global electronic payment network;retail contactless payment"),
    ("The Online Store That Made Selling Easier for Others",
     "Amazon began as an online bookstore and gradually built a marketplace where outside merchants could sell alongside its own retail operation. Third-party sellers expanded product choice, while fulfillment services helped some merchants store and ship goods through Amazon's network. The model creates convenience but also raises questions about fees, competition, and platform power. A marketplace grows when it makes participation valuable for both buyers and sellers.",
     "Amazon early online bookstore website;Amazon fulfillment warehouse;small business ecommerce packing"),
    ("The Company That Made Renting a Room Feel Normal",
     "Airbnb began by helping travelers find short-term stays in homes and spare rooms, offering an alternative to traditional hotels. Its platform connected hosts with guests and built trust through profiles, reviews, payments, and customer support. The model scaled without owning most of the accommodation itself, but it also created local debates about housing, regulation, and neighborhood impact. Platform growth depends on solving trust problems as well as matching supply and demand.",
     "Airbnb early founders apartment;Airbnb host room interior;vacation rental apartment keys"),
    ("The Software Company That Won Developers First",
     "Stripe built payment tools aimed at making it easier for developers and businesses to accept online payments. Clear documentation, APIs, and a relatively simple integration experience helped it spread among internet companies. Payment processing is complicated behind the scenes, involving fraud checks, banking relationships, and local rules. Stripe's story shows how a technical product can win customers by removing friction from a task that businesses need to get right.",
     "Stripe payments developer dashboard;software developer API code laptop;online checkout payment screen"),
    ("The Toy Company That Turned a Brick Into a Platform",
     "LEGO's building system works because pieces made decades apart can still connect in many ways. That compatibility turns individual sets into a larger creative platform: customers can combine parts, rebuild models, and invent their own designs. The company has expanded into games, films, and experiences, but the brick remains central to its identity. A consistent core product can support many new experiences without losing what makes it distinctive.",
     "LEGO interlocking bricks closeup;LEGO creative building workshop;LEGO classic sets collection"),
    ("The Retailer That Built Loyalty Around Low Prices",
     "Aldi built a discount grocery model around a focused product range, private-label goods, efficient stores, and relatively simple operations. Carrying fewer choices can make purchasing and inventory management easier, while customers trade some brand variety for lower prices. The model is not identical in every country, but the principle is consistent: remove costs customers may not value and protect the parts of the experience they do.",
     "Aldi supermarket private label shelves;discount grocery store checkout;Aldi shopping cart store"),
    ("The Company That Made a Shoe Famous With a Slogan",
     "Nike grew from a running-shoe business into a global sports brand through product design, athlete partnerships, and memorable marketing. Its famous slogan, 'Just Do It,' helped connect the brand with motivation and personal achievement rather than only technical footwear features. Advertising cannot replace product quality, but it can give customers a story to associate with a product. Brand meaning can become a competitive asset.",
     "Nike vintage running shoe;Nike Just Do It vintage advertising;athlete running track shoes"),
    ("The Search Engine That Sold Ads Beside Answers",
     "Google's advertising business grew around matching ads to search intent and charging advertisers when people interact with them. This made online advertising more measurable than many traditional formats, while search users could still access organic results. The model depends on relevance, trust, and a large volume of searches. It also creates ongoing questions about privacy, market power, and how clearly paid results should be identified.",
     "early Google search homepage;online search advertising dashboard;digital marketing analytics screen"),
    ("The Airline That Made a Simple Fare Its Strategy",
     "Southwest Airlines helped popularize a low-cost airline model in the United States through choices such as a relatively standardized fleet, quick aircraft turnarounds, and a focus on point-to-point routes. The model helped control costs and keep operations simple, although it has evolved over time and faces changing market conditions. The lesson is that a clear operating strategy can be more powerful than trying to offer every possible service.",
     "Southwest Airlines Boeing 737 aircraft;airline ground crew quick turnaround;Southwest Airlines early advertisement"),
])


# Further reserve inventory: ten more topics per channel for a 15-day runway
# at two scheduled runs per day, assuming one story per channel per run.
history_stories.extend([
    ("The Canal That Changed Global Shipping",
     "The Suez Canal opened in 1869, creating a direct sea route between the Mediterranean and the Red Sea. Ships no longer needed to sail around the southern tip of Africa when travelling between Europe and much of Asia. The canal shortened many journeys and became strategically important for trade and geopolitics. Its history also shows how infrastructure can reshape global commerce far beyond the country where it is built.",
     "Suez Canal 1869 historic opening;Suez Canal ships aerial;19th century canal construction"),
    ("The Great Fire That Reshaped London",
     "A fire began in a bakery on Pudding Lane in September 1666 and spread through much of the City of London. Wooden buildings, narrow streets, and strong winds helped the flames travel. The fire destroyed thousands of homes and many churches, including the old St Paul's Cathedral. Rebuilding changed parts of the city, but the disaster did not instantly create modern fire safety; reforms came gradually.",
     "Great Fire of London 1666 painting;Pudding Lane London historic;Christopher Wren rebuilding London"),
    ("The First Photograph Took Hours to Make",
     "In the 1820s or early 1830s, French inventor Nicéphore Niépce created one of the earliest surviving permanent photographs using a light-sensitive surface. The exposure took many hours, which is why the image is faint and the process was difficult to repeat. Photography later became faster through improvements in chemistry, lenses, and cameras. The first image was not a casual snapshot; it was the result of years of experimentation.",
     "View from the Window at Le Gras photograph;Nicéphore Niépce camera obscura;early photography plate"),
    ("The Ancient Trade Route That Was Never One Road",
     "The Silk Road was not a single paved highway running from China to Europe. It was a shifting network of land and sea routes used by merchants, travellers, diplomats, and religious communities. Goods such as silk, spices, glass, and metals moved along different paths depending on politics, geography, and demand. Ideas and technologies travelled too, making the network important for cultural exchange as well as commerce.",
     "Silk Road ancient trade route map;Silk Road camel caravan illustration;Central Asian historic bazaar"),
    ("The Stone Circle Built Across Many Generations",
     "Stonehenge was not built in one short construction project. Archaeological evidence shows that the monument developed through several phases over many centuries, beginning with earthworks before the large stones were arranged. People transported and positioned massive stones using techniques that researchers continue to study. Its exact purposes changed or remain debated, but the site clearly required planning, shared labour, and repeated rebuilding.",
     "Stonehenge aerial view;Stonehenge sarsen stones closeup;Stonehenge archaeological excavation"),
    ("The Flight That Lasted Only Twelve Seconds",
     "On December 17, 1903, Orville and Wilbur Wright made a powered flight at Kitty Hawk, North Carolina. The first flight lasted about twelve seconds and covered roughly 120 feet. It was not the first human attempt to fly, but it demonstrated controlled, powered, heavier-than-air flight using an aircraft the brothers had designed and tested. Their achievement grew from experiments with gliders, wings, and control systems.",
     "Wright brothers first flight 1903;Wright Flyer aircraft reconstruction;Kitty Hawk Wright brothers monument"),
    ("The Empire That Built Roads Across the Andes",
     "The Inca Empire developed an extensive road network across the Andes, connecting highland settlements, administrative centres, and coastal regions. The routes included stairs, bridges, and paths adapted to steep terrain. Runners and relay stations helped messages move across the empire, while storehouses supported officials and armies. The network shows how infrastructure can hold a state together even where mountains make travel difficult.",
     "Inca road Qhapaq Nan Andes;Inca rope bridge reconstruction;Inca trail stone steps"),
    ("The City That Preserved Its Past in a Cave",
     "The caves near Lascaux in France contain remarkable prehistoric paintings of animals, created roughly 17,000 years ago. The images were made with mineral pigments and placed across walls and ceilings, often in difficult-to-reach spaces. After the cave was opened to the public, changes in humidity and carbon dioxide threatened the paintings, so access was restricted and replicas were created. Preserving art can sometimes mean keeping visitors away from the original.",
     "Lascaux cave paintings horses;Lascaux prehistoric cave art;Lascaux cave replica hall"),
    ("The Manuscript That Helped Save an Ancient Language",
     "The Behistun Inscription in Iran contains a royal proclamation written in Old Persian, Elamite, and Babylonian cuneiform. Because the same message appeared in multiple languages, it helped scholars compare signs and work toward deciphering cuneiform writing. The inscription was carved high on a cliff, making study physically difficult. Like the Rosetta Stone, it shows how multilingual records can become keys to understanding the past.",
     "Behistun Inscription Iran cliff;Behistun cuneiform inscription closeup;ancient Persian relief"),
    ("The Bridge Built Without Modern Steel",
     "The Romans built durable stone bridges across rivers throughout their empire, using arches to distribute weight and foundations designed for local conditions. Some bridges remain in use or survive as major archaeological structures after many centuries. Not every Roman bridge was identical, and repairs and later rebuilding were common. Their legacy is less about one perfect design and more about practical engineering repeated across a huge territory.",
     "Roman stone bridge Alcantara;ancient Roman bridge arch;Roman bridge river engineering"),
])

business_stories.extend([
    ("The Assembly Line That Made Cars More Affordable",
     "Henry Ford did not invent the assembly line, but Ford Motor Company refined moving-line production for automobile manufacturing in the early twentieth century. Breaking complex work into repeatable steps helped reduce the time needed to assemble a Model T. The system also required careful coordination of parts, workers, and machinery. The broader lesson is that productivity often comes from redesigning the whole process rather than asking individuals to work faster.",
     "Ford Model T moving assembly line;historic Ford factory workers;Model T automobile production"),
    ("The Razor Company That Sold a Refill Habit",
     "King C. Gillette helped popularize the safety razor with inexpensive replaceable blades in the early twentieth century. The model made the handle a durable purchase while creating repeat demand for blades. The broader pattern became known as a razor-and-blades strategy, although many businesses use variations of it. It works only when customers see ongoing value and replacement parts remain convenient and trustworthy.",
     "vintage Gillette safety razor;early razor blade advertisement;classic shaving razor blades"),
    ("The Chocolate Company That Turned a Bar Into a Brand",
     "Cadbury grew from a small family business selling drinking chocolate into a major confectionery company. Its expansion involved product development, manufacturing investment, distribution, and distinctive packaging. The company also became associated with the model village of Bournville, built around its factory and employee welfare ideas. The story shows how a consumer brand can be shaped by production choices and the communities around its business.",
     "Cadbury vintage chocolate advertisement;Bournville Cadbury factory historic;classic chocolate bar packaging"),
    ("The Online Retailer That Made Fast Delivery a Membership",
     "Amazon Prime began as a paid membership offering faster shipping, then expanded to include digital services and other benefits. The bundle gives customers a reason to shop more often on one platform, while the company uses membership revenue and customer loyalty to support its wider retail ecosystem. The strategy is powerful but expensive to operate: delivery speed requires warehouses, logistics, and reliable last-mile networks.",
     "Amazon Prime delivery van;Amazon warehouse package conveyor;Amazon Prime membership screen"),
    ("The Phone Brand That Could Not Keep Its Lead",
     "BlackBerry became famous for secure mobile email and physical keyboards, especially among business users. As touchscreen smartphones and app ecosystems changed customer expectations, the company struggled to maintain its position in handsets. BlackBerry later shifted its focus toward software and security services. Its history is not simply about one product being better; it shows how a company's strengths can become less decisive when the market changes around them.",
     "BlackBerry classic keyboard phone;BlackBerry smartphone evolution;early business mobile email device"),
    ("The Pizza Chain That Made Ordering a Process",
     "Domino's expanded through a standardized operating model built around a focused menu, repeatable preparation, and delivery operations. The company later invested heavily in digital ordering and tracking, turning the customer experience into a technology problem as well as a food-service problem. Its growth shows how a service business can compete by making the entire process—from ordering to delivery—more predictable and convenient.",
     "Dominos Pizza delivery store;pizza chain kitchen preparation;online pizza order tracking screen"),
    ("The Retail Club That Makes Membership the Product",
     "Costco's warehouse-club model asks customers to pay an annual membership fee in exchange for access to bulk products and value pricing. Membership revenue helps support the business, while a focused range of products and high sales volume help keep operating costs under control. The model depends on customers believing they save enough to justify renewing. Loyalty is not automatic; it must be earned every year.",
     "Costco warehouse club interior;Costco membership card;bulk shopping warehouse shelves"),
    ("The Computer Company That Changed Its Business Model",
     "IBM began as a business-machine company and became a major force in computing through hardware, software, and services. Over time it shifted emphasis as customer needs changed, including moving away from some commodity hardware markets and investing in enterprise services and software. The company's history is not a straight line of success, but it illustrates how large organizations repeatedly have to decide which capabilities to keep and which businesses to leave.",
     "IBM early tabulating machine;IBM mainframe computer room;IBM historic computing advertisement"),
    ("The Game Console Rivalry That Changed Marketing",
     "The competition between Nintendo and Sega in the late 1980s and early 1990s helped shape the modern video-game console market. Both companies used distinctive characters, hardware features, and bold advertising to attract young players. Their rivalry was not only about technical specifications; it was about identity, exclusive games, and how a brand spoke to its audience. Competition can accelerate innovation when customers have meaningful alternatives.",
     "Nintendo Sega console rivalry;Sega Genesis Mega Drive console;Nintendo Super Nintendo console"),
    ("The Company That Made Shipping Containers Standard",
     "Standardized shipping containers transformed global trade by allowing goods to move between ships, trains, and trucks without being unpacked at every transfer. Entrepreneur Malcolm McLean helped drive containerization in the 1950s, and ports gradually redesigned cranes, terminals, and logistics around the new system. The result was faster handling and lower costs, but it required coordination across shipping companies, ports, and governments.",
     "Malcolm McLean shipping container;container ship port cranes;historic containerization cargo ship"),
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
