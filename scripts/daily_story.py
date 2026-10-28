import datetime, os

# High-retention, fact-grounded short stories. Keep history and business pools separate.
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

channel = os.environ.get("CHANNEL_NAME", "history").strip().lower()
if channel not in ("history", "business"):
    raise SystemExit("CHANNEL_NAME must be history or business")
channel_stories = history_stories if channel == "history" else business_stories

# Use the workflow run number so manual retries select a different story.
# Each channel has its own 14-story rotation and never uses the other channel's pool.
run_number = os.environ.get("GITHUB_RUN_NUMBER", "").strip()
if run_number.isdigit() and int(run_number) > 0:
    rotation_index = (int(run_number) - 1) % len(channel_stories)
    rotation_source = "workflow run " + run_number
else:
    day = datetime.datetime.now(datetime.timezone.utc).timetuple().tm_yday
    rotation_index = (day - 1) % len(channel_stories)
    rotation_source = "UTC day fallback"

title, video_script, image_searches = channel_stories[rotation_index]
with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as env:
    env.write("CHANNEL_NAME=" + channel + "\n")
    env.write("STORY_TOPIC=" + title + "\n")
    env.write("IMAGE_SEARCHES=" + image_searches + "\n")
    env.write("VIDEO_SCRIPT<<STORY_SCRIPT_EOF\n")
    env.write(video_script + "\n")
    env.write("STORY_SCRIPT_EOF\n")
print("Today's channel: " + channel)
print("Today's topic: " + title)
print("Topic rotation: " + str(rotation_index + 1) + "/" + str(len(channel_stories)))
print("Rotation source: " + rotation_source)
print("Script characters: " + str(len(video_script)))
