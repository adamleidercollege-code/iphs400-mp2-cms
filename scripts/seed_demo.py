#!/usr/bin/env python3
"""Create demo data so a grader (and you) can use the CMS immediately.

    uv run python scripts/seed_demo.py

T00 has nothing to seed. As you build content types, extend this so it creates:
  - one admin and one editor (passwords read from .env, never hard-coded)
  - a few posts and pages, at least one draft and one published

The rubric expects this to run clean on a fresh clone with .env.example values
(item E4), because the database itself is never committed.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db, models  # noqa: E402

# Continent -> Country -> Program -> body, each with its own clearly
# fictional description (T11 follow-up: no more "Placeholder copy").
CONTINENTS = {
    "Asia": {
        "description": (
            "Asia is home to CGE's two longest-running exchange partnerships, spanning a "
            "modern metropolis and a mountain-ringed former capital. Students here balance "
            "rigorous coursework with first-hand immersion in neighborhoods most visitors "
            "never see."
        ),
        "countries": {
            "Japan": {
                "description": (
                    "Kyoto's canals, temple gardens, and dense grid of family-run restaurants "
                    "make it one of the most walkable cities CGE sends students to. Expect a "
                    "slower pace outside the classroom, and a host-family culture that treats "
                    "language practice as a dinner-table sport."
                ),
                "programs": {
                    "Kyoto Exchange": (
                        "A semester based in the Higashiyama district, split between "
                        "Japanese-language seminars at a partner university and a weekly "
                        "fieldwork placement — recent cohorts have worked with a ceramics "
                        "studio, a city archive, and a neighborhood association planning a "
                        "summer festival."
                    ),
                },
            },
            "South Korea": {
                "description": (
                    "Seoul moves fast, and CGE's program is built around keeping up with it: "
                    "dense public transit, a 24-hour study-cafe culture, and a student body "
                    "that treats weekend hiking trips as seriously as exam prep."
                ),
                "programs": {
                    "Seoul Studies": (
                        "Coursework in Korean language and contemporary media runs alongside "
                        "an internship track — past placements include a webtoon publisher, "
                        "a language-exchange nonprofit, and a small-batch coffee roaster near "
                        "Hongdae."
                    ),
                },
            },
        },
    },
    "Africa": {
        "description": (
            "CGE's Africa partnerships sit on opposite coasts of the continent — a "
            "fieldwork-heavy program on the Indian Ocean side and an urban semester on the "
            "Atlantic side — and both lean on local organizations rather than a "
            "classroom-only model."
        ),
        "countries": {
            "Kenya": {
                "description": (
                    "Programs here are built around Nairobi's mix of university partnerships "
                    "and grassroots organizations, with fieldwork that regularly leaves the "
                    "city for rural sites a few hours out."
                ),
                "programs": {
                    "Nairobi Fieldwork": (
                        "Students split time between seminar coursework at a Nairobi partner "
                        "university and a placement with a community organization — recent "
                        "projects have covered water-access mapping, a youth sports league, "
                        "and a small-business microloan cooperative."
                    ),
                },
            },
            "South Africa": {
                "description": (
                    "Cape Town's program leans urban: coursework on the post-apartheid city, "
                    "internships across the city's nonprofit and arts sectors, and a long "
                    "list of weekend excursions along the coast."
                ),
                "programs": {
                    "Cape Town Semester": (
                        "A full semester combining university coursework with an internship "
                        "placement — students have worked with a township-based arts "
                        "nonprofit, a marine-conservation group, and a local radio station "
                        "covering city politics."
                    ),
                },
            },
        },
    },
    "Europe": {
        "description": (
            "CGE's two European programs sit at opposite ends of the academic spectrum — an "
            "intensive language immersion in Spain and a studio-and-seminar arts program in "
            "France — but both are built around small cohorts and a lot of independent city "
            "exploration."
        ),
        "countries": {
            "Spain": {
                "description": (
                    "Madrid's program is language-first: morning grammar and conversation "
                    "seminars, afternoons spent putting that Spanish to use across the city, "
                    "from the Mercado de San Miguel to the Reina Sofía."
                ),
                "programs": {
                    "Madrid Language Immersion": (
                        "An intensive Spanish-language track with a host-family placement, "
                        "built around daily conversation practice and a midterm research "
                        "project on a neighborhood of the student's choosing."
                    ),
                },
            },
            "France": {
                "description": (
                    "Paris Arts & Culture runs out of a partner institute near the Marais, "
                    "with coursework split between studio practice and art-history seminars "
                    "that make regular use of the city's museums."
                ),
                "programs": {
                    "Paris Arts & Culture": (
                        "A studio-and-seminar semester combining a working art studio, "
                        "museum-based art-history seminars, and a final portfolio show at the "
                        "partner institute."
                    ),
                },
            },
        },
    },
}

# A standalone Page's first paragraph heads the page; each "## Heading"
# below it renders as its own card (app/services/markdown.split_sections),
# so Staff get a structured layout by writing ordinary Markdown.
STANDALONE_PAGES = {
    "About CGE": (
        "The Kenyon Center for Global Engagement helps students find a program abroad, "
        "get ready to go, and make sense of it once they are back.\n\n"
        "This site is a demo build for IPHS 400 Mini-Project #2, not an official Kenyon "
        "page. The programs, countries, and student posts on it are invented, but "
        "the structure matches what a real CGE site would need.\n\n"
        "## Advising\n\n"
        "Talk through which programs fit your major, what credits transfer, and how a "
        "semester away fits the rest of your degree. Drop in during open hours or book a "
        "longer meeting.\n\n"
        "## Pre-departure and re-entry\n\n"
        "Required sessions before you go, covering visas, health, money, and safety, and "
        "a smaller one when you get back, where returning students compare notes with "
        "people about to leave.\n\n"
        "## Student ambassadors\n\n"
        "Students who have already been abroad write the posts on this site and "
        "answer questions from anyone considering the same program."
    ),
    "Contact Us": (
        "The demo CGE office is modeled on a ground-floor suite in Chalmers Library. "
        "Everything on this page is invented for a class project.\n\n"
        "## Email\n\n"
        "cge-demo@kenyon.edu\n\n"
        "A placeholder address. Nothing sent there reaches a real inbox.\n\n"
        "## Office\n\n"
        "Chalmers Library, ground floor\n\n"
        "Gambier, Ohio\n\n"
        "## Hours\n\n"
        "Monday to Friday, 9am to 4pm\n\n"
        "Drop-in advising runs Tuesday and Thursday afternoons. Other times by "
        "appointment."
    ),
}

# Cycled across the seeded Programs so the review-gate workflow (ADR-004) is
# visible on a fresh clone (T04 acceptance): at least one Post in each status.
POST_STATUSES = ["draft", "pending", "published"]

# Clearly fictional student Ambassadors who write the demo posts. The
# seeded editor account is one of them, so no account label ever shows up as
# a byline on the public site.
FICTIONAL_AMBASSADORS = [
    ("Maya Chen", "maya.chen@example.test"),
    ("Diego Ramirez", "diego.ramirez@example.test"),
    ("Amara Okafor", "amara.okafor@example.test"),
    ("Priya Patel", "priya.patel@example.test"),
    ("Liam O'Connor", "liam.oconnor@example.test"),
    ("Sofia Rossi", "sofia.rossi@example.test"),
]
FICTIONAL_AMBASSADOR_PASSWORD = "change-me-demo-ambassador"

# Three posts per Program, each with its own title, voice, Topic, author
# and date. The first entry of each list is written by the seeded editor
# account (so a grader logging in as the Ambassador has their own posts to
# edit) and cycles through draft/pending/published across the catalog; the
# other two are always published, so every Program page has something to show.
# All of it is invented for the demo — see the disclaimer in the footer.
PROGRAM_POSTS = {
    "Kyoto Exchange": [
        {
            "title": "Three weeks in, and the trains finally make sense",
            "topic": "general",
            "author": None,
            "days_ago": 12,
            "body": (
                "I spent my first week here getting on the right line in the wrong "
                "direction. Kyoto's network looked simple on the map in orientation, and "
                "then I met the express that skips the stop I actually needed.\n\n"
                "## What changed\n\n"
                "A classmate showed me that the platform signs colour-code the fast trains, "
                "which is the kind of thing nobody writes in a guide because everyone who "
                "lives here absorbed it as a child. Since then I have missed exactly one "
                "connection.\n\n"
                "> Week one you are a tourist with a timetable. Week three you are just "
                "someone on their way to class.\n\n"
                "The rest of settling in has been slower. I can order coffee without "
                "rehearsing, I know which convenience store has the good onigiri, and I have "
                "stopped converting every price back into dollars in my head."
            ),
        },
        {
            "title": "The 600-yen lunch that fixed my budget",
            "topic": "meals",
            "author": 0,
            "days_ago": 16,
            "body": (
                "My food budget was a disaster for the first fortnight. I was eating dinner "
                "out most nights because cooking in a shared kitchen felt like an imposition, "
                "and the yen adds up fast when every meal is a decision.\n\n"
                "Then one of the second-years took me to a teishoku place near the university "
                "gate: a set lunch, one price, rice and soup refilled without asking. It is "
                "six hundred yen and it is the single best thing that has happened to my "
                "spending.\n\n"
                "## How I eat now\n\n"
                "Set lunch on weekdays, cook properly twice a week, and save going out for "
                "the weekend, when there is someone to go with. That rhythm has cut my food "
                "spending by something like a third.\n\n"
                "> Nobody tells you that the cheapest meal of the day here is also the best "
                "one.\n\n"
                "The other lesson: the places with plastic food in the window and no English "
                "menu have been consistently kinder about my terrible Japanese than the ones "
                "that cater to visitors."
            ),
        },
        {
            "title": "Nobody raises their hand in my seminar",
            "topic": "academics",
            "author": 5,
            "days_ago": 40,
            "body": (
                "The first seminar I sat in on, I answered two questions and then realised "
                "nobody else had spoken. I assumed I had misread the room. I had, but not in "
                "the way I thought.\n\n"
                "Discussion here is not the performance it is at Kenyon. The professor asks "
                "something, there is a pause long enough to feel uncomfortable if you are used "
                "to American seminars, and then someone answers carefully, having actually "
                "thought about it first.\n\n"
                "## Adjusting\n\n"
                "I have learned to sit in the pause instead of filling it. My contributions "
                "are fewer and considerably better. Whether that survives the flight home is "
                "another question.\n\n"
                "> The silence is not empty. It is everyone composing a sentence they are "
                "willing to be held to.\n\n"
                "Written work is different too — one long essay at the end rather than weekly "
                "response papers, which means the reading piles up quietly until it doesn't."
            ),
        },
    ],
    "Seoul Studies": [
        {
            "title": "Why I picked the dorm over a goshiwon",
            "topic": "housing",
            "author": None,
            "days_ago": 8,
            "body": (
                "Housing was the decision I agonised over most before coming, and it turned "
                "out to be the one with the least information available. The program offers a "
                "dorm place; plenty of students rent a goshiwon room instead, which is cheaper "
                "and much smaller.\n\n"
                "## What I weighed\n\n"
                "The goshiwon would have saved me real money, and the independence appealed. "
                "But I would have been eating alone every night in a room the size of my "
                "bathroom at home, in a city where I knew nobody.\n\n"
                "I took the dorm. Three weeks later the people on my floor are the reason I "
                "have plans on weekends.\n\n"
                "> The cheaper room would have cost me the part of this semester I will "
                "actually remember.\n\n"
                "Ask me again in November, when I am sick of the shared kitchen, and I might "
                "give you a different answer."
            ),
        },
        {
            "title": "Study cafes are a social institution",
            "topic": "social-life",
            "author": 1,
            "days_ago": 30,
            "body": (
                "I arrived thinking a cafe was a place you went to avoid working. Here it is "
                "where the work happens, and it happens at hours that would be considered a "
                "cry for help at home.\n\n"
                "The place two streets over has individual desks, outlets at every seat, and "
                "a steady population at one in the morning during exam weeks. You buy a drink, "
                "you stay as long as you like, and nobody hovers.\n\n"
                "## The social part\n\n"
                "What surprised me is that going is not solitary. My classmates text the group "
                "chat, four people turn up, everyone works separately for three hours and then "
                "goes for food together. It is company without conversation, which is an "
                "underrated thing when you are tired and your language skills are spent.\n\n"
                "> You are not studying alone. You are studying near people, which turns out "
                "to be different."
            ),
        },
        {
            "title": "Two languages, one group project",
            "topic": "academics",
            "author": 2,
            "days_ago": 33,
            "body": (
                "My media course put me in a group with three Korean students for a project on "
                "streaming platforms. The brief said the presentation could be in either "
                "language. We ended up using both, badly, and then well.\n\n"
                "## How we split it\n\n"
                "They drafted the analysis in Korean because it was faster, I rewrote the "
                "English sections, and we spent two sessions reconciling arguments that had "
                "drifted apart in translation. That reconciling was the actual education.\n\n"
                "> Translating the argument forced us to find out whether we agreed, which we "
                "had assumed for a week and a half.\n\n"
                "We presented last Thursday. It went fine. More to the point, I have three "
                "people to sit with in a lecture hall of two hundred, which was not on the "
                "syllabus."
            ),
        },
    ],
    "Nairobi Fieldwork": [
        {
            "title": "Fieldwork notes are not essays",
            "topic": "academics",
            "author": None,
            "days_ago": 27,
            "body": (
                "My first set of field notes came back with more comments than content. Not "
                "because the observations were wrong, but because I had written them like a "
                "paper: argument first, evidence arranged to support it.\n\n"
                "## What the supervisor wanted\n\n"
                "What happened, in order, in plain language, with the things I was unsure "
                "about marked as unsure. The interpretation comes later, in a different "
                "document, where it can be argued with.\n\n"
                "> Write down what you saw before you decide what it means. You cannot "
                "un-decide later.\n\n"
                "It is a harder discipline than it sounds. I keep catching myself smoothing a "
                "detail because it complicates the story I already want to tell. The second "
                "set came back much cleaner."
            ),
        },
        {
            "title": "What I should have packed",
            "topic": "other",
            "author": 3,
            "days_ago": 22,
            "body": (
                "The packing list the program sends is accurate and incomplete, which is the "
                "worst combination because you trust it.\n\n"
                "## Things I brought and have not touched\n\n"
                "Three pairs of nice shoes. A travel iron. Enough medication for a year, which "
                "sat in customs for an afternoon while I explained it.\n\n"
                "## Things I wish I had brought\n\n"
                "A proper rain jacket, not the packable kind. A power bank, because fieldwork "
                "days are long and the phone is the camera, the map, and the notebook. Far "
                "more printed copies of documents than feels reasonable in 2026.\n\n"
                "> Everything you forgot can be bought here. Budget a week of looking for it, "
                "though.\n\n"
                "The real advice: pack for the version of yourself who is tired and in a hurry, "
                "not the one making a list on a calm afternoon in Gambier."
            ),
        },
        {
            "title": "Saturday football at the community centre",
            "topic": "social-life",
            "author": 4,
            "days_ago": 36,
            "body": (
                "The organisation I am placed with runs a youth football league on Saturdays. "
                "I turned up in week two to take photographs for their newsletter and have not "
                "missed one since.\n\n"
                "I am a poor footballer and that has been an advantage. Being visibly bad at "
                "something in front of people is a fast way past the stage where everyone is "
                "polite with you.\n\n"
                "## What I actually do there\n\n"
                "Mostly logistics: bibs, water, keeping the under-tens from reorganising the "
                "fixtures themselves. Occasionally I referee, which nobody respects and "
                "everybody argues with, exactly as it should be.\n\n"
                "> Three months of structured fieldwork taught me less about this neighbourhood "
                "than six Saturdays of being shouted at over a throw-in."
            ),
        },
    ],
    "Cape Town Semester": [
        {
            "title": "Learning to cook for eight",
            "topic": "meals",
            "author": None,
            "days_ago": 15,
            "body": (
                "Our flat share decided in the first week that we would eat together on "
                "weeknights, each of us cooking once. It sounded convivial. It is, and it is "
                "also a logistical education.\n\n"
                "## The maths nobody warned me about\n\n"
                "Cooking for one is improvisation. Cooking for eight is a plan: what scales, "
                "what does not, how long the one working oven actually takes, who has decided "
                "this month that they do not eat dairy.\n\n"
                "My first attempt was a curry that took two hours and fed six of the eight. My "
                "fourth was fine. The learning curve is steep and public.\n\n"
                "> Eight people eating badly together beats eight people eating well alone, up "
                "to a point, and we found the point in week three.\n\n"
                "We have since instituted a rule that whoever cooks does not wash up, which "
                "has done more for flat harmony than any house meeting."
            ),
        },
        {
            "title": "A flat share, four strangers, one kettle",
            "topic": "housing",
            "author": 0,
            "days_ago": 29,
            "body": (
                "The program places you in shared flats with people you have not met. Mine is "
                "two Kenyon students, one from a partner college, and a local student doing "
                "her honours year.\n\n"
                "The flat is good: high ceilings, terrible water pressure, a view of the "
                "mountain if you lean. What I did not anticipate is how much of living "
                "together is negotiating infrastructure.\n\n"
                "## The kettle problem\n\n"
                "There is one kettle, four people who want tea at the same hour, and a power "
                "arrangement that objects when the kettle and the heater run together. We have "
                "a rota now. I am aware of how that sounds.\n\n"
                "> Every shared flat runs on one unwritten agreement that nobody can articulate "
                "until somebody breaks it.\n\n"
                "Honestly the rota has been fine. The harder adjustment was learning that my "
                "housemate's honours deadlines are not negotiable around our weekend plans."
            ),
        },
        {
            "title": "The first month, in three lists",
            "topic": "general",
            "author": 2,
            "days_ago": 44,
            "body": (
                "I am bad at writing reflectively while a thing is still happening, so here is "
                "the first month as lists instead.\n\n"
                "## Harder than expected\n\n"
                "The time difference with home, and what it does to staying in touch. Reading "
                "a city whose recent history is visible in its layout and being a visitor "
                "inside that. Getting a local bank account.\n\n"
                "## Easier than expected\n\n"
                "Making friends in the cohort. The coursework, so far. Public transport, once "
                "I stopped being precious about asking for help.\n\n"
                "> Nothing about this semester has been difficult in the way the pre-departure "
                "workshop prepared me for, and plenty has been difficult in ways it did not "
                "mention.\n\n"
                "Ask me again at the end of term, when the long essays are due and the novelty "
                "has worn off."
            ),
        },
    ],
    "Madrid Language Immersion": [
        {
            "title": "I stopped apologising for my Spanish",
            "topic": "social-life",
            "author": None,
            "days_ago": 10,
            "body": (
                "For the first fortnight I opened every conversation by apologising for my "
                "Spanish. It is a reflex and it is a bad one: it turns a normal exchange into "
                "a performance review before anyone has said anything.\n\n"
                "## What I do instead\n\n"
                "I just start. If I get stuck, I say the word in English and someone supplies "
                "the Spanish one, and the conversation continues. People are far more patient "
                "with a bad sentence than with a preamble about how bad it is going to be.\n\n"
                "> The apology was not politeness. It was me asking to be let off before I had "
                "tried.\n\n"
                "My Spanish has improved more in the two weeks since I stopped than in the "
                "fortnight before, which I do not think is a coincidence."
            ),
        },
        {
            "title": "Lunch at two, dinner at ten",
            "topic": "meals",
            "author": 1,
            "days_ago": 12,
            "body": (
                "The eating schedule is the adjustment nobody takes seriously until they are "
                "standing outside a closed restaurant at seven in the evening, genuinely "
                "hungry, being told the kitchen opens at half eight.\n\n"
                "## Rebuilding the day\n\n"
                "Breakfast is small and early. Lunch is the real meal, around two, and it is "
                "long. Something small in the late afternoon keeps you going. Dinner is late "
                "and lighter than you expect.\n\n"
                "It took me about three weeks to stop being hungry at the wrong times. Now the "
                "idea of eating dinner at six seems faintly unhinged.\n\n"
                "> You do not adapt to the schedule by willpower. You adapt because the "
                "alternative is eating alone.\n\n"
                "My host mother finds my original timetable very funny and brings it up "
                "regularly with visitors."
            ),
        },
        {
            "title": "My host family has rules about the lift",
            "topic": "housing",
            "author": 3,
            "days_ago": 38,
            "body": (
                "Host family placements come with a document about expectations. It covers "
                "meals, laundry, guests, and quiet hours. It does not cover the lift, which is "
                "where I have made all my mistakes.\n\n"
                "## The unwritten rules\n\n"
                "You hold it for the neighbour on the third floor. You do not use it for one "
                "floor. You greet whoever is already inside, every time, and the greeting is "
                "not optional.\n\n"
                "Small things, and the building notices all of them. I got three weeks into "
                "silently riding up with people before my host mother gently explained that I "
                "had acquired a reputation.\n\n"
                "> The handbook tells you the rules your hosts can write down. The building "
                "teaches you the rest.\n\n"
                "I greet everyone now. The woman on the third floor has started saving me "
                "bread from the good bakery, so the system works."
            ),
        },
    ],
    "Paris Arts & Culture": [
        {
            "title": "Museum passes, bike locks, and other logistics",
            "topic": "other",
            "author": None,
            "days_ago": 34,
            "body": (
                "This is the unglamorous post. The program covers the interesting parts of "
                "being here; what it does not cover is the week of administrative setup that "
                "makes those parts possible.\n\n"
                "## The list, for whoever comes next\n\n"
                "Get the student museum pass in person during the first week, before term "
                "properly starts and the queue becomes an afternoon. Buy a bike lock that costs "
                "more than you think a bike lock should cost. Set up the transit app before you "
                "need it at a turnstile.\n\n"
                "> Every hour spent on logistics in week one buys back three in week six.\n\n"
                "None of this is hard. All of it is easier to do deliberately than at the "
                "moment you discover you needed it."
            ),
        },
        {
            "title": "Critique day in the studio",
            "topic": "academics",
            "author": 5,
            "days_ago": 21,
            "body": (
                "Critique here is slower and more formal than I am used to. Work goes up, "
                "everyone looks at it in silence for a genuinely long time, and then the "
                "discussion starts with description rather than judgement.\n\n"
                "## What gets said first\n\n"
                "Not whether it works. What is actually there — materials, scale, what the "
                "edges are doing. By the time anyone offers an opinion, the room has agreed on "
                "what it is looking at, which turns out to prevent most of the arguments I am "
                "used to having.\n\n"
                "> Describing the work before judging it sounds like a delay. It is the part "
                "that makes the judgement worth hearing.\n\n"
                "My first critique was uncomfortable. My second was the most useful hour of "
                "the semester so far."
            ),
        },
        {
            "title": "Six weeks of being slightly lost",
            "topic": "general",
            "author": 4,
            "days_ago": 31,
            "body": (
                "I have a good sense of direction at home and none at all here, and I have "
                "stopped treating that as a problem to solve.\n\n"
                "The studio is a twenty-minute walk from my flat and I have taken a different "
                "route most days. Some have been considerably longer than twenty minutes. One "
                "involved a canal I did not know existed.\n\n"
                "## What being lost is for\n\n"
                "Nothing, really, which is the point. The organised parts of this semester are "
                "organised well. The unstructured walking is where the city has stopped being a "
                "set of destinations and started being a place.\n\n"
                "> I know four ways to the studio now. Only one of them is efficient and it is "
                "the one I take least."
            ),
        },
    ],
}


def _seed_pages(admin_id: int) -> list[models.Page]:
    home = models.ensure_home_page()
    if models.list_children(home.id):
        print("Pages already seeded, leaving the tree as-is.")
        return [
            program
            for continent in models.list_children(home.id)
            for country in models.list_children(continent.id)
            for program in models.list_children(country.id)
        ]

    def _add(parent_id: int, title: str, body: str, show_in_footer: bool = False) -> models.Page:
        page = models.create_page(
            parent_id=parent_id, title=title, body=body,
            show_in_footer=show_in_footer, author_id=admin_id,
        )
        return models.publish_page(page.id)

    programs: list[models.Page] = []
    for continent_title, continent_data in CONTINENTS.items():
        continent = _add(home.id, continent_title, continent_data["description"])
        for country_title, country_data in continent_data["countries"].items():
            country = _add(continent.id, country_title, country_data["description"])
            for program_title, program_body in country_data["programs"].items():
                programs.append(_add(country.id, program_title, program_body))

    for standalone_title, body in STANDALONE_PAGES.items():
        _add(home.id, standalone_title, body, show_in_footer=True)

    print("Seeded the Continent -> Country -> Program tree and standalone pages.")
    return programs


def _ensure_fictional_ambassadors() -> list[models.User]:
    users = []
    for name, email in FICTIONAL_AMBASSADORS:
        user = models.get_user_by_email(email)
        if user is None:
            user = models.create_user(
                email=email, password=FICTIONAL_AMBASSADOR_PASSWORD,
                role="editor", display_name=name,
            )
        users.append(user)
    return users


def _days_ago(days: int) -> str:
    """An ISO timestamp in the shape SQLite writes, `days` back from now."""
    moment = datetime.now(timezone.utc) - timedelta(days=days)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _seed_posts(programs: list[models.Page], editor_id: int) -> None:
    """The three posts PROGRAM_POSTS defines for each Program. The one
    with `author: None` belongs to the seeded editor account and cycles
    through draft/pending/published across the catalog, so the admin side has
    a Post in every status to work with (T04); the other two are always
    published, so every Program page has something to show. Each Post is
    backdated to its own day, so the public site reads like a term's writing
    rather than eighteen posts filed at once.
    """
    if not programs or any(models.list_posts_by_program(p.id) for p in programs):
        print("Posts already seeded (or no programs to seed under), leaving as-is.")
        return

    ambassadors = _ensure_fictional_ambassadors()

    for i, program in enumerate(programs):
        specs = PROGRAM_POSTS.get(program.title)
        if not specs:
            continue
        anchor_status = POST_STATUSES[i % len(POST_STATUSES)]
        for spec in specs:
            is_anchor = spec["author"] is None
            author_id = editor_id if is_anchor else ambassadors[spec["author"]].id
            status = anchor_status if is_anchor else "published"
            post = models.create_post(
                program_id=program.id, title=spec["title"], body=spec["body"],
                topic=spec["topic"], author_id=author_id,
            )
            if status in ("pending", "published"):
                models.set_post_status(post.id, from_status="draft", to_status="pending")
            if status == "published":
                models.set_post_status(post.id, from_status="pending", to_status="published")
            models.backdate_post(post.id, _days_ago(spec["days_ago"]))

    total = sum(len(PROGRAM_POSTS.get(p.title, [])) for p in programs)
    print(f"Seeded {total} posts across Topics, authors, dates, and statuses "
          "(draft/pending/published) under the seeded Programs.")


def _seed_deactivated_users_with_drafts(programs: list[models.Page]) -> None:
    """T06 acceptance: one already-deactivated Ambassador and one
    already-deactivated Staff member, each seeded by creating the account
    active, giving them a draft Post, and then deactivating them — so the
    cascade actually runs rather than just hard-coding the end state. The
    Ambassador's draft is deleted by the cascade; the Staff member's is left
    in place, same as any other Staff member's unfinished work.
    """
    if not programs:
        print("No programs to seed deactivated-user drafts under, leaving as-is.")
        return
    if models.get_user_by_email("deactivated-ambassador@example.test") is not None:
        print("Deactivated demo users already seeded, leaving as-is.")
        return

    program = programs[0]
    ambassador = models.create_user(
        email="deactivated-ambassador@example.test", password="change-me-deactivated",
        role="editor", display_name="Former Ambassador",
    )
    models.create_post(
        program_id=program.id, title="Half-finished post",
        body="Still drafting — notes to self before writing the real thing.",
        topic="general", author_id=ambassador.id,
    )
    models.deactivate_user(ambassador.id)

    staff = models.create_user(
        email="deactivated-staff@example.test", password="change-me-deactivated",
        role="admin", display_name="Former Staff",
    )
    models.create_post(
        program_id=program.id, title="CGE's unfinished draft",
        body="Still drafting — notes to self before writing the real thing.",
        topic="general", author_id=staff.id,
    )
    models.deactivate_user(staff.id)

    print("Seeded a deactivated Ambassador (draft deleted by the cascade) and "
          "a deactivated Staff member (draft left in place).")


def main() -> int:
    admin_pw = os.environ.get("CMS_ADMIN_PASSWORD")
    editor_pw = os.environ.get("CMS_EDITOR_PASSWORD")
    deactivated_pw = os.environ.get("CMS_DEACTIVATED_PASSWORD", "change-me-deactivated")
    if not admin_pw or not editor_pw:
        print("Set CMS_ADMIN_PASSWORD and CMS_EDITOR_PASSWORD in .env "
              "(copy .env.example).")
        return 1

    db.init_db()
    for email, pw, role, name, active in [
        ("admin@example.test", admin_pw, "admin", "Dana Whitfield", True),
        ("editor@example.test", editor_pw, "editor", "Jordan Avery", True),
        ("deactivated@example.test", deactivated_pw, "editor", "Deactivated Demo", False),
    ]:
        if models.get_user_by_email(email) is None:
            models.create_user(email=email, password=pw, role=role,
                                display_name=name, active=active)
    print("Seeded admin, editor, and deactivated demo users.")

    admin = models.get_user_by_email("admin@example.test")
    editor = models.get_user_by_email("editor@example.test")
    programs = _seed_pages(admin.id)
    _seed_posts(programs, editor.id)
    _seed_deactivated_users_with_drafts(programs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
