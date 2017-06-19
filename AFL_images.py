import os
import csv
import sys
import jinja2
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
from PIL import Image
from bs4 import BeautifulSoup

import cloudinary
import cloudinary.uploader
import cloudinary.api

class Create_AFL_Questions():

    def process_csv(self):
        inputfile_path = os.path.join(self.CSVpath,self.input_csv)

        with open(inputfile_path) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    if row["Round"] != "":
                        self.round = row["Round"]
                        self.populate_fixture(row["Round"])
                except KeyError:
                    pass

                try:
                    if row["Home_Team"] != "":
                        print((row["Home_Team"], row['Away_Team']))
                        self.create_home_away_question(row['Home_Team'], row['Away_Team'])
                except KeyError:
                    pass

                try:
                    if row['MMHome_Player'] != "":
                        self.create_mars_matchup_question(row['MMHome_Player'], row['Home_Team'], row['MMAway_Player'], row['Away_Team'], row["MM_Stat"])
                except KeyError:
                    pass

                try:
                    if row['HHHome_Player'] != "":
                        self.create_supercoach_headtohead_question(row['HHHome_Player'], row['Home_Team'], row['HHAway_Player'], row['Away_Team'])
                except KeyError:
                    pass

                try:
                    if row['Player_Team'] != "":
                        self.create_player_in_question(row['Player'], row['Player_Team'])
                except KeyError:
                    pass


        outputfile_path = os.path.join(self.CSVpath,"Output - " + self.input_csv)
        with open(outputfile_path, 'w') as csvfile:
            fieldnames = ["Question title", 'Question text', 'filename', 'url']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(self.csv_output_dicts)

    def create_player_in_question(self, player, team):
        self.active_question_dict = {}
        team = self.find_cannonical_team_name(team)

        image_url = self.single_player_image(player, team)
        team_nickname = self.find_cannonical_team_name(team, "nickname")

        TEMPLATE_FILE = 'player_playing_question.html'
        template = self.templateEnv.get_template( TEMPLATE_FILE )
        outputText = template.render(image_url = image_url,
                                     player = player,
                                     team_nickname = team_nickname).replace("\n", "")

        self.active_question_dict['Question title'] = "Round %s: Will %s play for the %s next match?" %(self.round, player, team_nickname)
        self.active_question_dict['Question text'] = (outputText)

        self.csv_output_dicts.append(self.active_question_dict)

    def create_home_away_question(self, home_team, away_team):

        self.active_question_dict = {}

        home_team_nickname = self.find_cannonical_team_name(home_team,"nickname")
        away_team_nickname = self.find_cannonical_team_name(away_team,"nickname")

        fixture = self.find_fixture_dict(home_team)

        image_url = self.team_matchup_images(home_team, away_team)

        TEMPLATE_FILE = 'home_away_question.html'
        template = self.templateEnv.get_template( TEMPLATE_FILE )
        outputText = template.render(image_url = image_url,
                                     home_team_nickname = home_team_nickname,
                                     away_team_nickname = away_team_nickname,
                                     match_date = fixture['match_date'],
                                     match_time = fixture['match_time'],
                                     venue = fixture['venue']).replace("\n", "")

        self.active_question_dict['Question title'] = "Round %s: %s vs %s" %(self.round, home_team_nickname, away_team_nickname)
        self.active_question_dict['Question text'] = (outputText)

        self.csv_output_dicts.append(self.active_question_dict)

    def create_mars_matchup_question(self,home_player, home_team, away_player, away_team, stat):

        self.active_question_dict = {}

        home_team_nickname = self.find_cannonical_team_name(home_team,"nickname")
        away_team_nickname = self.find_cannonical_team_name(away_team,"nickname")

        image_url =  self.player_matchup_images(home_player, home_team, away_player, away_team)

        TEMPLATE_FILE = 'mars_matchup_question.html'
        template = self.templateEnv.get_template( TEMPLATE_FILE )
        outputText = template.render(image_url = image_url,
                                     home_team_nickname = home_team_nickname,
                                     away_team_nickname = away_team_nickname,
                                     home_player = home_player,
                                     away_player = away_player,
                                     round = str(self.round)).replace("\n", "")

        self.active_question_dict['Question title'] = "Round %s: Will %s get more %s than %s?" %(self.round, home_player, stat, away_player)
        self.active_question_dict['Question text'] = (outputText)

        self.csv_output_dicts.append(self.active_question_dict)


    def create_supercoach_headtohead_question(self,home_player, home_team, away_player, away_team):

        self.active_question_dict = {}

        home_team_nickname = self.find_cannonical_team_name(home_team,"nickname")
        away_team_nickname = self.find_cannonical_team_name(away_team,"nickname")

        image_url =  self.player_matchup_images(home_player, home_team, away_player, away_team)

        TEMPLATE_FILE = 'supercoach_headtohead_question.html'
        template = self.templateEnv.get_template( TEMPLATE_FILE )
        outputText = template.render(image_url = image_url,
                                     home_team_nickname = home_team_nickname,
                                     away_team_nickname = away_team_nickname,
                                     home_player = home_player,
                                     away_player = away_player,
                                     round = str(self.round)
                                     ).replace("\n", "")

        self.active_question_dict['Question title'] = "Round %s: Will %s get more supercoach points than %s?" %(self.round, home_player, away_player)
        self.active_question_dict['Question text'] = (outputText)

        self.csv_output_dicts.append(self.active_question_dict)


    def populate_fixture(self, round):

        fixture_html = urlopen("http://www.afl.com.au/fixture?roundId=CD_R2017014%s#tround" %(round)).read()
        fixture_soup = BeautifulSoup(fixture_html, "html.parser")

        fixture_table = fixture_soup.find("div", {"id": "tround"} ).find("table", {"class": "fixture"})

        rows = fixture_table.find("tbody").find_all("tr")

        match_date = ""
        for row in rows:
            if row.find("td") == None:
                match_date = row.find("th").text
            else:
                home_team = row.find("div", {"class": "team-logos"}).find("span", {"class": "home"}).text
                away_team = row.find("div", {"class": "team-logos"}).find("span", {"class": "away"}).text
                venue = row.find("a", {"class": "venue"}).text
                match_time = row.find("span", {"class": "time"}).text

                self.fixture_list.append({"teams": (home_team, away_team),
                                          "venue": venue,
                                          "match_date": match_date,
                                          "match_time": match_time,
                                          "round": round})


    def team_matchup_images(self, team1_name, team2_name):

        team1_name = self.find_cannonical_team_name(team1_name)
        team2_name = self.find_cannonical_team_name(team2_name)

        team1_image_path = os.path.join(self.assetpath,"%s.png" %team1_name)
        team2_image_path = os.path.join(self.assetpath,"%s.png" %team2_name)
        versus_path = os.path.join(self.assetpath,"versus200px.png")

        result = self.merge_triple_images(team1_image_path, versus_path, team2_image_path)
        return self.save_image(result, "teams_%s_v_%s.png" %(team1_name, team2_name))

    def player_matchup_images(self, player_1_name, player_1_team, player_2_name, player_2_team):
        versus_path = os.path.join(self.assetpath,"versus317px.png")

        if player_1_name != "":

            player_1_image_url = self.find_player_image_url(player_1_name, player_1_team)
            player_2_image_url = self.find_player_image_url(player_2_name, player_2_team)

            # If no url is found, see if teams were backwards
            if player_1_image_url == None:
                player_1_image_url = self.find_player_image_url(player_1_name, player_2_team)
            if player_2_image_url == None:
                player_2_image_url = self.find_player_image_url(player_2_name, player_1_team)

            if player_1_image_url == None:
                player_1_image_url = self.find_player_image_url(player_1_name, player_1_team, manual_input=True)
            if player_2_image_url == None:
                player_2_image_url = self.find_player_image_url(player_2_name, player_2_team, manual_input=True)


            try:
                player_1_image_path = urlopen(player_1_image_url)
                player_2_image_path = urlopen(player_2_image_url)

                result = self.merge_triple_images(player_1_image_path, versus_path, player_2_image_path)
                return self.save_image(result, "players_%s_%s_v_%s_%s.png" %(player_1_name, player_1_team, player_2_name, player_2_team))

            except AttributeError:
                print('Could not complete for %s and %s matchup' %(player_1_name, player_2_name))

    def single_player_image(self, player_1_name, player_1_team):

        if player_1_name != "":

            player_1_image_url = self.find_player_image_url(player_1_name, player_1_team)

            try:
                player_1_image_path = urlopen(player_1_image_url)


                image1 = Image.open(player_1_image_path)

                (width1, height1) = image1.size

                result_width = width1
                result_height = height1

                result = Image.new('RGBA', (result_width, result_height))
                result.paste(im=image1, box=(0, 0))

                return self.save_image(result, "singe_player_%s_%s.png" %(player_1_name, player_1_team))

            except AttributeError:
                print('Could not complete for %s' %(player_1_name))


    def find_player_image_url(self, player_name, team_name, manual_input = False):

        if manual_input == False:
            team_url = self.find_team_url(team_name)
            split_name = player_name.lower().replace('-','').split(' ')
            player_url_name = split_name[0] + '-' + split_name[-1]
            total_url = 'http://' + team_url + 'player-profile/' + player_url_name
            try:
                return self.get_profile_url(total_url)
            except HTTPError:
                return None

        else:
            while True:
                url = input("Unable to find profile for %s of %s, please provide url manually (type 'skip' to skip):" %(player_name, team_name))
                if url == "skip":
                    return None
                else:
                    try:
                        total_url = 'http://www.' + url
                        return self.get_profile_url(total_url)
                    except HTTPError:
                        pass
                    except URLError:
                        pass



    def get_profile_url(self,total_url):
            profile_html = urlopen(total_url).read()
            profile_soup = BeautifulSoup(profile_html, "html.parser")
            profile_element = profile_soup.findAll("img", { "class" : "pp-picture" })[0]
            profile_url = profile_element['src']
            return profile_url


    def merge_triple_images(self, file1_path, file2_path, file3_path):

        file1 = Image.open(file1_path)
        file2 = Image.open(file2_path)
        file3 = Image.open(file3_path)

        (width1, height1) = file1.size
        (width2, height2) = file2.size
        (width3, height3) = file3.size

        result_width = width1 + width2 + width3
        result_height = max(height1, height2, height3)

        result = Image.new('RGBA', (result_width, result_height))
        result.paste(im=file1, box=(0, 0))
        result.paste(im=file2, box=(width1, 0))
        result.paste(im=file3, box=(width1 + width2, 0))

        return result

    def save_image(self, image, filename):

        image.save(os.path.join(self.outputpath,filename))
        if self.upload_to_cloud == True:
            cloud_url = cloudinary.uploader.upload((os.path.join(self.outputpath,filename)))
            self.active_question_dict['filename'] = filename
            self.active_question_dict['url'] = cloud_url['url']

            return cloud_url['url']
        else:
            return ""

    def find_cannonical_team_name(self, orginal_input, name_type = "short"):
        Team_names = [
            ('ESS', 'Bombers', 'Essendon'),
            ('GEEL', 'Cats', 'Geelong'),
            ('ADEL', 'Crows', 'Adelaide'),
            ('MELB', 'Demons', 'Melbourne'),
            ('FRE', 'Dockers', 'Fremantle', 'Freo'),
            ('WB', 'Bulldogs', 'Western', 'Dogs', 'Western Bulldogs'),
            ('WCE', 'Eagles', 'West Coast'),
            ('GWS', 'Giants', 'GWS'),
            ('HAW', 'Hawks', 'Hawthorn'),
            ('NMFC', 'Kangaroos', 'North Melbourne', 'North', 'Roos'),
            ('BL', 'Lions', 'Brisbane'),
            ('COLL', 'Magpies', 'Collingwood', 'Pies'),
            ('PORT', 'Power', 'Port Adelaide', 'Port'),
            ('STK', 'Saints', 'St Kilda', 'Stkilda'),
            ('GCFC', 'Suns', 'Gold Coast'),
            ('SYD', 'Swans', 'Sydney'),
            ('RICH', 'Tigers', 'Richmond'),
            ('CARL', 'Blues', 'Carlton')
        ]

        while True:
            for name in Team_names:
                if orginal_input in name:
                    if name_type == "nickname":
                        return name[1]
                    elif name_type == "location":
                        return name[2]
                    elif name_type == "full":
                        return name[2] + name[1]
                    else:
                        return name[0]

            orginal_input = input("Typo in team name %s, please provide manually:" %orginal_input)

        return None

    def find_team_url(self, orginal_input):
        input_name = self.find_cannonical_team_name(orginal_input)

        Team_names = [
            ('ESS', 'www.essendonfc.com.au/'),
            ('GEEL', 'www.geelongcats.com.au/'),
            ('ADEL', 'www.afc.com.au/'),
            ('MELB', 'www.melbournefc.com.au/'),
            ('FRE', 'www.fremantlefc.com.au/'),
            ('WB', 'www.westernbulldogs.com.au/'),
            ('WCE', 'www.westcoasteagles.com.au/'),
            ('GWS', 'www.gwsgiants.com.au/'),
            ('HAW', 'www.hawthornfc.com.au/'),
            ('NMFC', 'www.nmfc.com.au/'),
            ('BL', 'www.lions.com.au/'),
            ('COLL', 'www.collingwoodfc.com.au/'),
            ('PORT', 'www.portadelaidefc.com.au/'),
            ('STK', 'www.saints.com.au/'),
            ('GCFC', 'www.goldcoastfc.com.au/'),
            ('SYD', 'www.sydneyswans.com.au/'),
            ('RICH', 'www.richmondfc.com.au/'),
            ('CARL', 'www.carltonfc.com.au/')
        ]

        for name in Team_names:
            if input_name in name:
                return name[1]


    def find_fixture_dict(self,team):

        team = self.find_cannonical_team_name(team)
        for match in self.fixture_list:
            if team in match['teams']:
                return match

    def __init__(self, input_csv, upload_to_cloud = True):

        self.assetpath = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Image_assets'))
        self.CSVpath = os.path.abspath(os.path.join(os.path.dirname(__file__), 'CSVs'))
        self.outputpath = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Image_results'))
        self.csv_output_dicts = []
        self.active_question_dict = {}
        self.round = 1

        self.input_csv = input_csv
        self.upload_to_cloud = upload_to_cloud

        self.fixture_list = []

        templateLoader = jinja2.FileSystemLoader( searchpath="./Templates")
        self.templateEnv = jinja2.Environment( loader=templateLoader )




if __name__ == '__main__':

    cloudinary.config(
      cloud_name = "slowvoice",
      api_key = "723548748512687",
      api_secret = "9I-0LTB0wRVvx6CGALVG-Hb40rU"
    )



    question_creator = Create_AFL_Questions("Example.csv")
    question_creator.process_csv()




